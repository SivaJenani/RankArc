"""
llm_extractor.py – AI-powered question extraction with multi-paper-set support.

New capabilities:
  1. Metadata extraction: exam name, sections/categories, number of paper sets,
     duration (if stated in document).
  2. Multi-set detection: for files containing N complete exam papers, each question
     is tagged with paper_set (e.g. "2026-10-10 Shift 1").
  3. No arbitrary question cap – all questions from the chosen set are extracted.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# In-memory tracking of processing progress per paper_id
_PAPER_PROGRESS: dict[int, dict[str, Any]] = {}


def set_paper_progress(paper_id: int, progress: int, step: str) -> None:
    _PAPER_PROGRESS[paper_id] = {
        "progress": max(0, min(100, progress)),
        "step": step,
    }


def get_paper_progress(paper_id: int) -> dict[str, Any]:
    return _PAPER_PROGRESS.get(paper_id, {"progress": 0, "step": "Starting…"})

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_META_SYSTEM_PROMPT = """\
You are an exam document analyser. Given the raw text of an exam file, extract:
1. Exam title / name (string)
2. Sections / categories (array of objects with "name", "q_start", "q_end", "count")
3. Paper sets – if the document contains multiple complete exam papers (e.g. different
   dates / shifts), list each one as an object with "label" (human-readable, e.g.
   "10 Oct 2026 Shift 1"), "q_count" (number of questions in that set).
4. Duration in minutes (integer or null if not stated).

Return ONLY valid JSON (no markdown fences) with this exact shape:
{
  "exam_title": "<string>",
  "categories": [
    {"name": "<string>", "q_start": <int>, "q_end": <int>, "count": <int>}
  ],
  "paper_sets": [
    {"label": "<string>", "q_count": <int>}
  ],
  "duration_minutes": <int or null>
}

If there is only one paper (not a compilation), paper_sets should contain exactly one
entry. If you cannot determine a field, use null or an empty array.
"""

_EXTRACT_SYSTEM_PROMPT = """\
You are a question parser. Extract ALL questions from the given exam text segment.
Return ONLY a valid JSON array – no markdown fences, no commentary.

Each element must have this exact shape:
{
  "question_number": <int>,
  "question_text": "<string>",
  "question_type": "mcq" | "true_false",
  "explanation": "<string or null>",
  "options": [
    {"label": "A", "option_text": "<string>", "is_correct": <bool>},
    {"label": "B", "option_text": "<string>", "is_correct": <bool>},
    ...
  ]
}

Rules:
- question_number must be a positive integer.
- Exactly one option per question must have is_correct=true.
- For true/false questions use labels A (True) and B (False).
- If you cannot parse a question, skip it rather than guessing.
- Do NOT include any text outside the JSON array.
- Extract EVERY question you can find – do not stop early.
"""


# ---------------------------------------------------------------------------
# Regex fallback helpers
# ---------------------------------------------------------------------------

def _regex_extract_meta(raw_text: str) -> dict[str, Any]:
    """Best-effort metadata extraction without an LLM."""
    # 1. Search for date/shift sets across the entire text
    shift_matches = list(re.finditer(
        r'(?:SSC CGL[^\n\)]*\(HELD ON:\s*([^\n\)]+)\))|(?:HELD ON:\s*([^\n\)]+)\))',
        raw_text,
        re.IGNORECASE,
    ))
    sets: list[dict] = []
    for m in shift_matches:
        raw_label = (m.group(1) or m.group(2)).strip()
        clean_label = " ".join(raw_label.split())
        if clean_label and not any(s['label'].upper() == clean_label.upper() for s in sets):
            sets.append({"label": clean_label, "q_count": 100})

    if not sets:
        # Generic date/shift pattern: e.g. "10 October 2026 Shift 1" or "10 Oct 2026 Shift 1"
        date_pattern = re.compile(
            r'\b(\d{1,2}\s+[A-Za-z]+\s+20\d{2})\s*(?:[-–]|\s+)\s*(Shift\s*\d)?',
            re.IGNORECASE,
        )
        for m in date_pattern.finditer(raw_text):
            dt = m.group(1).strip()
            sh = m.group(2).strip() if m.group(2) else ""
            label = f"{dt} {sh}".strip()
            if label and not any(s['label'].upper() == label.upper() for s in sets):
                sets.append({"label": label, "q_count": 100})

    # 2. Categories / Sections:
    has_ssc = bool(re.search(r'SSC|CGL', raw_text, re.IGNORECASE))
    has_gi = bool(re.search(r'GENERAL\s*INT', raw_text, re.IGNORECASE))
    has_qa = bool(re.search(r'QUANTITATIVE', raw_text, re.IGNORECASE))
    has_en = bool(re.search(r'ENGLISH', raw_text, re.IGNORECASE))

    categories: list[dict] = []
    if has_ssc or (has_gi and (has_qa or has_en)):
        categories = [
            {"name": "General Intelligence", "q_start": 1, "q_end": 25, "count": 25},
            {"name": "General Awareness", "q_start": 26, "q_end": 50, "count": 25},
            {"name": "Quantitative Aptitude (Basic Arithmetic Skill)", "q_start": 51, "q_end": 75, "count": 25},
            {"name": "English Language (Basic Knowledge)", "q_start": 76, "q_end": 100, "count": 25},
        ]
    else:
        # Generic section detection
        sec_pattern = re.compile(
            r'([A-Z\s]{4,40})\s*\n\s*(?:0?1\.)',
            re.MULTILINE,
        )
        for m in sec_pattern.finditer(raw_text):
            name = m.group(1).strip()
            if name and not any(c['name'] == name for c in categories):
                categories.append({"name": name, "q_start": 1, "q_end": 25, "count": 25})

    # 3. Duration:
    # Look for explicit duration or default to standard 60 minutes for 100-question papers
    dur_match = re.search(r'Duration[:\s]*(\d+)\s*(hour|hr|minute|min)', raw_text[:8000], re.IGNORECASE)
    duration_minutes: int | None = None
    if dur_match:
        val = int(dur_match.group(1))
        unit = dur_match.group(2).lower()
        duration_minutes = val * 60 if 'hour' in unit or 'hr' in unit else val
    elif categories or (sets and sets[0].get("q_count") == 100):
        duration_minutes = 60  # Standard 60 mins (1 Hour) for 100 questions

    # 4. Exam title:
    title_m = re.search(r'(SSC CGL\s*20\d{2})', raw_text, re.IGNORECASE)
    if title_m:
        exam_title = f"{title_m.group(1).upper()} Mock Test Series"
    else:
        title_lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        exam_title = title_lines[0] if title_lines else "Competitive Mock Exam"

    return {
        "exam_title": exam_title,
        "categories": categories,
        "paper_sets": sets if sets else [{"label": "Paper 1", "q_count": None}],
        "duration_minutes": duration_minutes,
    }


def _regex_extract_questions(raw_text: str, paper_set: str | None = None) -> list[dict[str, Any]]:
    """
    Heuristic rule-based parser for exam PDFs extracted with layout=True.

    Key improvements over the old version:
    - Question numbers may have up to 12 leading spaces (layout=True indents content)
    - Options (A)(B)(C)(D) may appear on the same line: "(A) foo  (B) bar"
    - Option text is trimmed of trailing whitespace artifacts from layout padding
    - Correct answer is derived from the "Ans: X" marker; fallback to first option
    - Questions with ≥2 options and a non-trivial stem are accepted
    """
    # Match question blocks: optional leading spaces, then N. <body>
    # Body runs until the next question number at same/lesser indent, or end of text
    q_pattern = re.compile(
        r'(?:^|\n)[ \t]{0,12}(\d{1,3})\.[ \t]+(.+?)(?=\n[ \t]{0,12}\d{1,3}\.[ \t]+|\Z)',
        re.DOTALL,
    )

    # Option: (A) text — text ends at next option tag, Ans:, or newline with no indent
    # Handles both same-line "(A) foo  (B) bar" and separate-line "(A) foo\n(B) bar"
    opt_pattern = re.compile(r'\(([A-D])\)[ \t]*([^\n(]+)', re.IGNORECASE)

    ans_pattern = re.compile(r'\bAns\b[:\s.]*([A-D])\b', re.IGNORECASE)

    parsed: list[dict[str, Any]] = []

    for m in q_pattern.finditer(raw_text):
        num_str = m.group(1)
        body = m.group(2)

        # Find correct answer
        ans_m = ans_pattern.search(body)
        correct_lbl = ans_m.group(1).upper() if ans_m else None

        # Remove "Ans: X" markers from body before option parsing
        body_clean = ans_pattern.sub('', body)

        # Extract options in order A → B → C → D
        opts: list[dict[str, Any]] = []
        labels_seen: set[str] = set()
        for om in opt_pattern.finditer(body_clean):
            lbl = om.group(1).upper()
            if lbl in labels_seen:
                continue
            labels_seen.add(lbl)
            opt_text = om.group(2).strip()
            # Strip trailing layout-padding spaces (runs of 3+ spaces before next token)
            opt_text = re.sub(r'\s{3,}.*$', '', opt_text).strip()
            if not opt_text:
                continue
            opts.append({
                'label': lbl,
                'option_text': opt_text,
                'is_correct': lbl == correct_lbl if correct_lbl else False,
            })

        # Question text = everything before the first option
        first_opt_m = opt_pattern.search(body_clean)
        q_text_raw = body_clean[:first_opt_m.start()] if first_opt_m else body_clean
        # Collapse whitespace: replace newlines/tabs/multiple-spaces with single space
        q_text = re.sub(r'[ \t]+', ' ', q_text_raw.replace('\n', ' ')).strip()

        # Require at least 2 options and a meaningful stem (> 8 chars)
        if len(opts) < 2 or len(q_text) < 8:
            continue

        # If no "Ans:" was found, default correct to first option
        if not any(o['is_correct'] for o in opts):
            opts[0]['is_correct'] = True

        entry: dict[str, Any] = {
            'question_number': int(num_str),
            'question_text': q_text,
            'question_type': 'mcq',
            'explanation': f'Correct Answer: Option {correct_lbl or opts[0]["label"]}',
            'options': opts,
        }
        if paper_set:
            entry['paper_set'] = paper_set
        parsed.append(entry)

    return parsed


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _llm_extract_meta(raw_text: str, api_key: str) -> dict[str, Any]:
    """Call Claude to extract paper metadata."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        # Only look at first ~8000 chars for meta – the headers/TOC are at the start
        snippet = raw_text[:8000]
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=_META_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": snippet}],
        )
        raw = message.content[0].text.strip() if message.content else "{}"
        raw = raw.strip("` \n").lstrip("json").strip()
        return json.loads(raw)
    except Exception as exc:
        logger.warning("LLM meta extraction failed: %s; using regex fallback", exc)
        return _regex_extract_meta(raw_text)


def _llm_extract_questions(text_chunk: str, api_key: str, paper_set: str | None = None) -> list[dict[str, Any]]:
    """Call Claude to extract questions from a text chunk."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            system=_EXTRACT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Extract all questions:\n\n{text_chunk}"}],
        )
        raw = message.content[0].text.strip() if message.content else "[]"
        raw = raw.strip("` \n").lstrip("json").strip()
        data = json.loads(raw)
        questions = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        if paper_set:
            for q in questions:
                q['paper_set'] = paper_set
        return questions
    except Exception as exc:
        logger.warning("LLM question extraction failed: %s; using regex fallback", exc)
        return _regex_extract_questions(text_chunk, paper_set=paper_set)


# ---------------------------------------------------------------------------
# Segment splitter for multi-set files
# ---------------------------------------------------------------------------

def _split_by_sets(raw_text: str, paper_sets: list[dict]) -> list[tuple[str, str]]:
    """
    For multi-set compilations, split the text by exam date/shift headers.
    Returns [(set_label, text_chunk), ...].
    Falls back to treating entire text as one chunk if split fails.
    """
    if not paper_sets or len(paper_sets) <= 1:
        label = paper_sets[0]["label"] if paper_sets else "Paper 1"
        return [(label, raw_text)]

    # Build split points by looking for each set label in the text
    boundaries: list[tuple[int, str]] = []
    for s in paper_sets:
        label = s["label"]
        # Match label with flexible whitespace case-insensitively
        pattern = r'\s+'.join(re.escape(part) for part in label.strip().split())
        m = re.search(pattern, raw_text, re.IGNORECASE)
        if m:
            boundaries.append((m.start(), label))
        else:
            # Fallback: date part only
            date_part = re.sub(r'Shift\s*\d', '', label, flags=re.IGNORECASE).strip()
            if date_part:
                dp_pattern = r'\s+'.join(re.escape(part) for part in date_part.split())
                m_dp = re.search(dp_pattern, raw_text, re.IGNORECASE)
                if m_dp:
                    boundaries.append((m_dp.start(), label))

    if not boundaries:
        # Cannot split – return whole text under first label
        return [(paper_sets[0]["label"], raw_text)]

    boundaries.sort()
    chunks: list[tuple[str, str]] = []
    for i, (start, label) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(raw_text)
        chunks.append((label, raw_text[start:end]))
    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_meta_and_questions(
    raw_text: str,
    api_key: str,
    paper_id: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Returns (meta_dict, all_questions_list).
    meta_dict keys: exam_title, categories, paper_sets, duration_minutes
    Each question dict has an optional 'paper_set' key.
    """
    has_llm = bool(api_key and "your-key-here" not in api_key)

    # 1. Extract metadata
    if paper_id:
        set_paper_progress(paper_id, 25, "Analyzing exam headers and section structure…")
    if has_llm:
        meta = _llm_extract_meta(raw_text, api_key)
    else:
        meta = _regex_extract_meta(raw_text)

    paper_sets: list[dict] = meta.get("paper_sets") or [{"label": "Paper 1", "q_count": None}]

    # 2. Split text into per-set chunks
    chunks = _split_by_sets(raw_text, paper_sets)
    total_chunks = max(len(chunks), 1)

    # 3. Extract questions from each chunk
    all_questions: list[dict[str, Any]] = []
    for idx, (label, chunk) in enumerate(chunks):
        if paper_id:
            pct = 30 + int(55 * ((idx + 1) / total_chunks))
            set_paper_progress(paper_id, pct, f"Extracting questions from {label} ({idx + 1}/{total_chunks})…")

        # Claude has a ~200k token context; 40k chars ≈ 10k tokens – safe per chunk
        # For very large chunks, process in 40k-char windows
        CHUNK_SIZE = 40_000
        if len(chunk) <= CHUNK_SIZE:
            parts = [chunk]
        else:
            parts = [chunk[i:i + CHUNK_SIZE] for i in range(0, len(chunk), CHUNK_SIZE)]

        seen_numbers: set[int] = set()
        for part in parts:
            if has_llm:
                qs = _llm_extract_questions(part, api_key, paper_set=label)
            else:
                qs = _regex_extract_questions(part, paper_set=label)
            # Deduplicate by question_number within this set
            for q in qs:
                num = q.get("question_number", 0)
                if num not in seen_numbers:
                    seen_numbers.add(num)
                    all_questions.append(q)

    return meta, all_questions


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def process_paper(
    paper_id: int,
    file_path: str,
    settings: Any = None,
) -> None:
    """Background task: extract text → metadata + questions → save to DB → update paper status."""
    from app.config import get_settings
    from app.db import SessionLocal
    from app.models.paper import Paper, PaperStatus
    from app.models.question import Option, Question
    from app.services.parser import extract_text

    if settings is None:
        settings = get_settings()

    set_paper_progress(paper_id, 5, "Upload complete. Initializing parser…")

    async with SessionLocal() as db:
        async def _set_status(status: str) -> None:
            result = await db.execute(select(Paper).where(Paper.id == paper_id))
            paper = result.scalar_one_or_none()
            if paper:
                paper.status = status
                paper.updated_at = datetime.utcnow()
                await db.commit()

        try:
            await _set_status(PaperStatus.processing)
            set_paper_progress(paper_id, 12, "Extracting text and pages from document…")

            # 1. First attempt structured PDF extraction with diagram crops
            from app.services.exam_extractor import extract_exam_paper
            import asyncio
            loop = asyncio.get_event_loop()

            meta = None
            question_dicts = []

            if file_path.lower().endswith(".pdf"):
                set_paper_progress(paper_id, 20, "Extracting shifts, questions, and diagrams from PDF…")
                try:
                    meta, question_dicts = await loop.run_in_executor(
                        None,
                        extract_exam_paper,
                        file_path,
                        paper_id,
                        settings.upload_dir,
                    )
                except Exception as ex:
                    logger.warning("extract_exam_paper failed: %s; falling back to parser", ex)

            # 2. Fallback to generic text extraction if structured PDF extractor didn't produce questions
            if not question_dicts:
                set_paper_progress(paper_id, 30, "Extracting text and pages from document…")
                raw_text = await loop.run_in_executor(None, extract_text, file_path)

                if not raw_text.strip():
                    logger.warning("No text extracted from paper %s", paper_id)
                    set_paper_progress(paper_id, 0, "No text extracted from document.")
                    await _set_status(PaperStatus.failed)
                    return

                meta, question_dicts = await loop.run_in_executor(
                    None,
                    extract_meta_and_questions,
                    raw_text,
                    settings.anthropic_api_key,
                    paper_id,
                )

            if not question_dicts:
                logger.warning("All extraction methods failed for paper %s", paper_id)
                set_paper_progress(paper_id, 0, "Could not identify questions in paper.")
                await _set_status(PaperStatus.failed)
                return

            # 3. Save metadata to paper
            set_paper_progress(paper_id, 88, "Structuring exam details…")
            result = await db.execute(select(Paper).where(Paper.id == paper_id))
            paper_obj = result.scalar_one_or_none()
            if paper_obj:
                paper_obj.meta = json.dumps(meta)
                await db.commit()

            # 4. Persist questions and options
            set_paper_progress(paper_id, 92, f"Saving {len(question_dicts)} parsed questions to database…")
            for q_data in question_dicts:
                question = Question(
                    paper_id=paper_id,
                    question_number=int(q_data.get("question_number", 0)),
                    question_text=str(q_data.get("question_text", "")),
                    question_type=str(q_data.get("question_type", "mcq")),
                    image_url=q_data.get("image_url"),
                    explanation=q_data.get("explanation"),
                    paper_set=q_data.get("paper_set"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(question)
                await db.flush()

                correct_option_id: int | None = None
                for opt_data in q_data.get("options", []):
                    option = Option(
                        question_id=question.id,
                        label=str(opt_data.get("label", "")),
                        option_text=str(opt_data.get("option_text", "")),
                        image_url=opt_data.get("image_url"),
                        is_correct=bool(opt_data.get("is_correct", False)),
                    )
                    db.add(option)
                    await db.flush()
                    if option.is_correct:
                        correct_option_id = option.id

                if correct_option_id is not None:
                    question.correct_option_id = correct_option_id

            await db.commit()
            set_paper_progress(paper_id, 100, f"Ready! Extracted {len(question_dicts)} questions.")
            await _set_status(PaperStatus.ready)

        except Exception as exc:
            logger.exception("Failed to process paper %s: %s", paper_id, exc)
            set_paper_progress(paper_id, 0, f"Failed: {exc}")
            try:
                await _set_status(PaperStatus.failed)
            except Exception:
                pass

"""Conservative, zero-cost MCQ extraction. Unknown answers stay unknown."""
import re
from collections import Counter
from typing import Any

Q_START = re.compile(r"(?m)^[ \t]*(?:Q(?:uestion)?[ \t]*\.?[ \t]*)?(\d{1,4})[ \t]*[.)、:][ \t]*(?=\S|$)", re.I)
OPTION = re.compile(r"(?<!\S)(?:\(([A-Ea-e1-5])\)|([A-Ea-e])[.)\]:])[ \t]*")
ANSWER = re.compile(r"\b(?:Ans(?:wer)?(?:\s+key)?|Correct\s+(?:answer|option))\s*[:.\-]?\s*(?:Option\s*)?\(?([A-Ea-e1-5])\)?\b", re.I)
KEY_HEADING = re.compile(r"(?im)^\s*(?:answer\s+key|answers|solutions)\s*:?[ \t]*$")
SET_HEADING = re.compile(r"(?im)^\s*(?:(?:paper|set|shift)\s+(?:[A-Z]|\d+)(?:[^\n]{0,70})|[^\n]{0,70}\bHELD\s+ON\s*:[^\n]+)\s*$")
SECTION = re.compile(r"(?im)^\s*(?:section\s+[A-Z0-9]+[^\n]*|general intelligence|general awareness|quantitative aptitude|english language)\s*$")


def label(value):
    return chr(64 + int(value)) if value.isdigit() else value.upper()


def parse_block(number: int, body: str) -> dict | None:
    answer_match = ANSWER.search(body)
    correct = label(answer_match.group(1)) if answer_match else None
    explanation_match = re.search(r"\b(?:Explanation|Solution)\s*:\s*(.*)", body, re.I | re.S)
    explanation = explanation_match.group(1).strip() if explanation_match else None
    end = min([m.start() for m in (answer_match, explanation_match) if m] or [len(body)])
    body = body[:end].strip()
    matches = list(OPTION.finditer(body))
    # Require an A,B,... or (1),(2),... sequence. Reject ambiguous repeated labels.
    if len(matches) < 2 or [label(m.group(1) or m.group(2)) for m in matches] != list("ABCDE"[:len(matches)]):
        return None
    stem = body[:matches[0].start()].strip()
    if not stem:
        return None
    options = []
    for i, match in enumerate(matches):
        text = body[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(body)].strip()
        if not text:
            return None
        lbl = label(match.group(1) or match.group(2))
        options.append({"label": lbl, "option_text": text, "is_correct": lbl == correct})
    if correct and correct not in [o["label"] for o in options]:
        return None
    return {"question_number": number, "question_text": stem, "question_type": "mcq",
            "explanation": explanation, "options": options}


def extract_questions(raw_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_text = raw_text.replace("\r\n", "\n").replace("\xa0", " ")
    key_match = KEY_HEADING.search(raw_text)
    key = {}
    body = raw_text
    if key_match:
        body = raw_text[:key_match.start()]
        key_text = raw_text[key_match.end():]
        for m in re.finditer(r"\b(\d{1,4})\s*[.):\-]?\s*\(?([A-Ea-e])\)?(?=\s|[,;]|$)", key_text):
            num, val = int(m.group(1)), m.group(2).upper()
            if num in key and key[num] != val:
                raise ValueError("The answer key contains conflicting answers. Please check it.")
            key[num] = val
    starts = list(Q_START.finditer(body))
    headings = list(SET_HEADING.finditer(body))
    sections = list(SECTION.finditer(body))
    questions = []
    warnings = []
    skipped = []
    group_counts = Counter()
    category_counts = Counter()
    seen = set()
    implicit = 1
    last_num = None
    last_explicit = None
    for i, start in enumerate(starts):
        number = int(start.group(1))
        if number < 1:
            continue
        end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
        chunk = body[start.end():end]
        # Do not attach the next shift or section heading to the last option.
        next_heads = [m.start() for m in headings + sections if start.end() <= m.start() < end]
        if next_heads:
            chunk = body[start.end():min(next_heads)]
        question = parse_block(number, chunk)
        if question is None:
            skipped.append(number)
            continue
        preceding = [m for m in headings if m.start() < start.start()]
        explicit = " ".join(preceding[-1].group().split()) if preceding else None
        if explicit != last_explicit:
            implicit = 1
            last_num = None
        if last_num is not None and number <= last_num:
            if explicit:
                raise ValueError(f"Question {number} repeats in {explicit}. Split repeated sections into separate files.")
            implicit += 1
        group = explicit or f"Paper {implicit}"
        if (group, number) in seen:
            raise ValueError(f"Duplicate question {number} in {group}. Please check numbering.")
        seen.add((group, number))
        last_num, last_explicit = number, explicit
        question["paper_set"] = group
        # A single trailing key is ambiguous across multiple sets. Never reuse it silently.
        if key and not ANSWER.search(chunk):
            if number in key:
                for option in question["options"]:
                    option["is_correct"] = option["label"] == key[number]
                if not any(o["is_correct"] for o in question["options"]):
                    raise ValueError(f"The answer key references a missing option for question {number}.")
        questions.append(question)
        group_counts[group] += 1
        preceding_sec = [m for m in sections if m.start() < start.start()]
        name = " ".join(preceding_sec[-1].group().split()) if preceding_sec else "Questions"
        category_counts[name] += 1
    if key and len(group_counts) > 1:
        raise ValueError("A shared answer key is ambiguous across multiple sets. Upload one set with its key at a time.")
    if not questions:
        raise ValueError("No complete multiple-choice questions found. Use numbered questions with options A-D (or (1)-(4)).")
    if skipped:
        # Partial success must never quietly become a shorter, apparently complete exam.
        raise ValueError(f"Could not safely split question(s) {', '.join(map(str, skipped[:12]))}. Check their numbering/options or upload a clearer file.")
    unknown = sum(not any(o["is_correct"] for o in q["options"]) for q in questions)
    if unknown:
        warnings.append(f"{unknown} question(s) have no answer key. Mark their correct answers in Review before starting a scored test.")
    warnings.append("Check extracted questions and options against the source before starting. Diagrams and complex layouts may need manual review.")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    title = lines[0] if lines and not Q_START.match(lines[0]) else "Uploaded paper"
    dur = re.search(r"\b(?:duration|time)\s*:?\s*(\d+)\s*(hours?|hrs?|minutes?|mins?)\b", body[:8000], re.I)
    duration = int(dur.group(1)) * (60 if dur.group(2).lower().startswith(("h",)) else 1) if dur else None
    meta = {"exam_title": title, "paper_sets": [{"label": k, "q_count": v} for k, v in group_counts.items()],
            "categories": [{"name": k, "count": v} for k, v in category_counts.items()],
            "duration_minutes": duration, "warnings": warnings,
            "extraction_method": "local-text-or-tesseract", "unkeyed_questions": unknown}
    return meta, questions

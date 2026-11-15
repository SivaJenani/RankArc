"""Background extraction with local parsers/OCR only. No external model calls."""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.services.local_extractor import extract_questions

logger = logging.getLogger(__name__)
_PAPER_PROGRESS: dict[int, dict[str, Any]] = {}
_PROCESSING_LOCK = asyncio.Lock()


def set_paper_progress(paper_id, progress, step):
    _PAPER_PROGRESS[paper_id] = {"progress": max(0, min(100, progress)), "step": step}


def get_paper_progress(paper_id):
    return _PAPER_PROGRESS.get(paper_id, {"progress": 0, "step": "Waiting for processing"})


def extract_meta_and_questions(raw_text, api_key="", paper_id=None):
    # api_key remains an ignored compatibility parameter. Never spend credits.
    return extract_questions(raw_text)


def _read_document(file_path, paper_id, settings):
    import fitz
    from app.services.parser import extract_text
    from app.services.scan_extractor import extract_scanned_paper
    if file_path.lower().endswith(".pdf"):
        with fitz.open(file_path) as doc:
            if doc.needs_pass:
                raise ValueError("This PDF is locked. Upload an unlocked copy.")
            if len(doc) > 300:
                raise ValueError("Split this document into files of at most 300 pages.")
            # A scanned page anywhere, not just the cover, selects image-first mode.
            any_graphics = any(bool(p.get_images()) or bool(p.get_drawings()) for p in doc)
            scanned = any(len(p.get_text().strip()) < 40 and bool(p.get_images()) for p in doc)
        if scanned or any_graphics:
            return extract_scanned_paper(file_path, paper_id, settings.upload_dir,
                                        lambda p, s: set_paper_progress(paper_id, p, s))
    raw = extract_text(file_path)
    if not raw.strip():
        raise ValueError("No readable content found. Upload a clearer scan, searchable PDF or DOCX.")
    set_paper_progress(paper_id, 75, "Splitting questions and preserving options")
    return extract_questions(raw)


async def process_paper(paper_id, file_path, settings=None):
    from app.config import get_settings
    from app.db import SessionLocal
    from app.models.paper import Paper, PaperStatus
    from app.models.question import Option, Question
    settings = settings or get_settings()
    set_paper_progress(paper_id, 5, "Queued for local extraction")
    # One OCR job at a time on a small/free instance. Other requests stay responsive.
    async with _PROCESSING_LOCK:
        async with SessionLocal() as db:
            try:
                paper = await db.get(Paper, paper_id)
                if not paper:
                    return
                if paper.status == PaperStatus.ready:
                    return
                existing = (await db.execute(select(Question.id).where(Question.paper_id == paper_id).limit(1))).first()
                if existing:
                    raise ValueError("This upload already has questions. It was not overwritten.")
                paper.status = PaperStatus.processing
                await db.commit()
                set_paper_progress(paper_id, 12, "Reading document locally")
                meta, questions = await asyncio.to_thread(_read_document, file_path, paper_id, settings)
                set_paper_progress(paper_id, 88, f"Saving {len(questions)} questions")
                # All question writes and metadata commit together. No partial paper.
                paper.meta = json.dumps(meta)
                for entry in questions:
                    question = Question(paper_id=paper_id, question_number=entry["question_number"],
                        question_text=entry["question_text"], question_type=entry.get("question_type", "mcq"),
                        image_url=entry.get("image_url"), explanation=entry.get("explanation"),
                        paper_set=entry.get("paper_set"), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
                    db.add(question)
                    await db.flush()
                    for item in entry["options"]:
                        option = Option(question_id=question.id, label=item["label"], option_text=item["option_text"],
                                        image_url=item.get("image_url"), is_correct=item.get("is_correct", False))
                        db.add(option)
                        await db.flush()
                        if option.is_correct:
                            question.correct_option_id = option.id
                paper.status = PaperStatus.ready
                paper.updated_at = datetime.utcnow()
                await db.commit()
                set_paper_progress(paper_id, 100, f"Ready: {len(questions)} questions. Review before testing.")
            except Exception as exc:
                await db.rollback()
                logger.exception("Extraction failed for paper %s", paper_id)
                # Do not leak paths, stack traces or server configuration to the UI.
                reason = str(exc) if isinstance(exc, ValueError) else "The document could not be processed. Try an unlocked, valid PDF or DOCX."
                paper = await db.get(Paper, paper_id)
                if paper:
                    paper.status = PaperStatus.failed
                    paper.meta = json.dumps({"processing_error": reason})
                    await db.commit()
                set_paper_progress(paper_id, 0, reason)

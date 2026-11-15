import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import get_current_user
from app.db import get_db
from app.models.paper import Paper, PaperStatus
from app.models.question import Option, Question
from app.models.user import User
from app.schemas.papers import PaperRead
from app.schemas.questions import QuestionRead, QuestionUpdate
from app.services.file_handler import save_upload_file
from app.services.llm_extractor import get_paper_progress, process_paper

logger = logging.getLogger(__name__)

router = APIRouter(tags=["papers"])

_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


@router.get("/", response_model=list[PaperRead])
async def list_papers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaperRead]:
    """List all papers belonging to the current user, with question counts."""
    q_count = (
        select(Question.paper_id, func.count(Question.id).label("cnt"))
        .group_by(Question.paper_id)
        .subquery()
    )
    result = await db.execute(
        select(Paper, func.coalesce(q_count.c.cnt, 0).label("question_count"))
        .outerjoin(q_count, q_count.c.paper_id == Paper.id)
        .where(Paper.owner_id == current_user.id)
        .order_by(Paper.created_at.desc())
    )
    rows = result.all()
    papers_out: list[PaperRead] = []
    for paper, qcount in rows:
        papers_out.append(
            PaperRead(
                id=paper.id,
                title=paper.title,
                filename=paper.filename,
                status=paper.status,
                created_at=paper.created_at,
                question_count=qcount,
            )
        )
    return papers_out


@router.post("/upload", response_model=PaperRead, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaperRead:
    """Upload a PDF or DOCX file, persist metadata, and trigger AI processing."""
    settings = get_settings()

    ext = ""
    if file.filename:
        _, ext = os.path.splitext(file.filename)
        ext = ext.lower()

    content_type_ok = file.content_type in _ALLOWED_CONTENT_TYPES
    ext_ok = ext in _ALLOWED_EXTENSIONS

    if not content_type_ok and not ext_ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are supported.",
        )

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File exceeds the 100 MB limit.",
        )

    filename, file_path = await save_upload_file(file, current_user.id, settings.upload_dir)

    title = title.strip() or file.filename or filename
    paper = Paper(
        owner_id=current_user.id,
        title=title,
        filename=filename,
        file_path=file_path,
        status=PaperStatus.uploading,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    background_tasks.add_task(process_paper, paper.id, file_path, settings)

    return PaperRead(
        id=paper.id,
        title=paper.title,
        filename=paper.filename,
        status=paper.status,
        created_at=paper.created_at,
        question_count=0,
    )


@router.get("/{paper_id}/meta")
async def get_paper_meta(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return the extracted metadata for a paper:
    exam_title, categories, paper_sets, duration_minutes.
    Also returns distinct paper_set labels found in questions.
    """
    paper = await _get_owned_paper(paper_id, current_user.id, db)

    meta: dict = {}
    if paper.meta:
        try:
            meta = json.loads(paper.meta)
        except Exception:
            pass

    # Also derive distinct set labels from actual questions stored
    result = await db.execute(
        select(Question.paper_set, func.count(Question.id).label("cnt"))
        .where(Question.paper_id == paper.id)
        .group_by(Question.paper_set)
    )
    rows = result.all()
    stored_counts = {r[0]: r[1] for r in rows if r[0]}

    ordered_sets = []
    meta_sets = meta.get("paper_sets") or []
    for ms in meta_sets:
        lbl = ms.get("label")
        if lbl in stored_counts:
            ordered_sets.append({"label": lbl, "q_count": stored_counts[lbl]})
        else:
            ordered_sets.append({"label": lbl, "q_count": ms.get("q_count", 100)})

    if not ordered_sets and rows:
        ordered_sets = [{"label": r[0] or "Paper 1", "q_count": r[1]} for r in rows]

    return {
        "paper_id": paper.id,
        "title": paper.title,
        "exam_title": meta.get("exam_title") or paper.title,
        "categories": meta.get("categories") or [],
        "paper_sets": ordered_sets if ordered_sets else [{"label": "Paper 1", "q_count": len(rows)}],
        "duration_minutes": meta.get("duration_minutes"),
    }


@router.get("/{paper_id}/questions", response_model=list[QuestionRead])
async def get_questions(
    paper_id: int,
    paper_set: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuestionRead]:
    """
    Return questions for a paper.
    Optional ?paper_set=<label> filters to a specific set.
    """
    paper = await _get_owned_paper(paper_id, current_user.id, db)

    stmt = select(Question).where(Question.paper_id == paper.id)
    if paper_set:
        stmt = stmt.where(Question.paper_set == paper_set)
    stmt = stmt.order_by(Question.question_number)

    result = await db.execute(stmt)
    questions = result.scalars().all()

    out: list[QuestionRead] = []
    for q in questions:
        options_result = await db.execute(
            select(Option).where(Option.question_id == q.id).order_by(Option.label)
        )
        opts = options_result.scalars().all()
        out.append(QuestionRead.model_validate({
            "id": q.id,
            "question_number": q.question_number,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "explanation": q.explanation,
            "correct_option_id": q.correct_option_id,
            "image_url": q.image_url,
            "paper_set": q.paper_set,
            "options": opts,
        }))
    return out


@router.put("/{paper_id}/questions/{question_id}", response_model=QuestionRead)
async def update_question(
    paper_id: int,
    question_id: int,
    payload: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionRead:
    """Update question text, explanation, correct answer, and/or options."""
    await _get_owned_paper(paper_id, current_user.id, db)

    result = await db.execute(
        select(Question).where(Question.id == question_id, Question.paper_id == paper_id)
    )
    question: Question | None = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if payload.question_text is not None:
        question.question_text = payload.question_text
    if payload.explanation is not None:
        question.explanation = payload.explanation
    if payload.correct_option_id is not None:
        question.correct_option_id = payload.correct_option_id
    question.updated_at = datetime.utcnow()

    if payload.options is not None:
        opts_result = await db.execute(select(Option).where(Option.question_id == question.id))
        for old_opt in opts_result.scalars().all():
            await db.delete(old_opt)

        new_correct_id: int | None = None
        for opt_data in payload.options:
            new_opt = Option(
                question_id=question.id,
                label=opt_data.label,
                option_text=opt_data.option_text,
                is_correct=opt_data.is_correct,
            )
            db.add(new_opt)
            await db.flush()
            if new_opt.is_correct:
                new_correct_id = new_opt.id

        if new_correct_id and payload.correct_option_id is None:
            question.correct_option_id = new_correct_id

    await db.commit()
    await db.refresh(question)

    opts_result = await db.execute(
        select(Option).where(Option.question_id == question.id).order_by(Option.label)
    )
    opts = opts_result.scalars().all()
    return QuestionRead.model_validate({
        "id": question.id,
        "question_number": question.question_number,
        "question_text": question.question_text,
        "question_type": question.question_type,
        "explanation": question.explanation,
        "correct_option_id": question.correct_option_id,
        "options": opts,
    })


@router.get("/{paper_id}/status")
async def get_paper_status(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the processing status, progress percentage, and current step."""
    paper = await _get_owned_paper(paper_id, current_user.id, db)
    progress_info = get_paper_progress(paper_id)

    if paper.status == "ready":
        return {"status": "ready", "progress": 100, "step": "Done! Paper is ready."}

    if paper.status == "failed":
        return {"status": "failed", "progress": 0, "step": "Processing failed."}

    # Paper is 'processing' or 'uploading' — check if in-memory progress exists
    mem_progress = progress_info.get("progress", 0)
    mem_step = progress_info.get("step", "")

    # If no in-memory progress (e.g. server restarted mid-job), the background
    # task is gone. Mark the paper failed so the frontend can recover cleanly.
    if mem_progress == 0 and paper.status == "processing":
        # Auto-recover: mark as failed so the user is prompted to re-upload
        paper.status = "failed"
        paper.updated_at = datetime.utcnow()
        await db.commit()
        return {"status": "failed", "progress": 0, "step": "Server restarted during processing. Please upload again."}

    return {
        "status": paper.status,
        "progress": mem_progress or 10,
        "step": mem_step or "Processing document…",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_owned_paper(paper_id: int, user_id: int, db: AsyncSession) -> Paper:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper: Paper | None = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    if paper.owner_id is None:
        paper.owner_id = user_id
        await db.commit()
    elif paper.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return paper

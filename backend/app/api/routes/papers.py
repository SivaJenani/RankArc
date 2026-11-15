import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pathlib import Path
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
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}
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

    if not ext_ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are supported.",
        )

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size == 0:
        raise HTTPException(status_code=422, detail="The file is empty.")
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

    ordered_sets = [{"label": r[0] or "Paper 1", "q_count": r[1]} for r in rows]
    return {
        "paper_id": paper.id, "title": paper.title,
        "exam_title": meta.get("exam_title") or paper.title,
        "categories": meta.get("categories") or [],
        "paper_sets": ordered_sets,
        "duration_minutes": meta.get("duration_minutes"),
        "warnings": meta.get("warnings", []),
        "extraction_method": meta.get("extraction_method"),
        "unkeyed_questions": meta.get("unkeyed_questions", 0),
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

    from app.models.attempt import AttemptAnswer
    used = (await db.execute(select(AttemptAnswer.id).where(AttemptAnswer.question_id == question.id).limit(1))).first()
    if used:
        raise HTTPException(status_code=409, detail="This question has recorded attempts. Upload a revised paper to preserve past results.")
    opts_result = await db.execute(select(Option).where(Option.question_id == question.id))
    old_options = {o.id: o for o in opts_result.scalars().all()}
    correct_id = payload.correct_option_id if "correct_option_id" in payload.model_fields_set else question.correct_option_id
    if correct_id is not None and correct_id not in old_options:
        raise HTTPException(status_code=422, detail="Correct answer must belong to this question.")
    if payload.options is not None:
        incoming = payload.options
        if not 2 <= len(incoming) <= 5 or [o.label for o in incoming] != list("ABCDE"[:len(incoming)]):
            raise HTTPException(status_code=422, detail="Options must be ordered A-D, A-E or another complete A-starting sequence.")
        ids = [o.id for o in incoming]
        if any(i is None or i not in old_options for i in ids) or len(set(ids)) != len(ids) or set(ids) != set(old_options):
            raise HTTPException(status_code=422, detail="Option identities must match the existing question.")
        for item in incoming:
            if not item.option_text.strip():
                raise HTTPException(status_code=422, detail="Option text cannot be empty.")
        for item in incoming:
            option = old_options[item.id]
            option.label = item.label
            option.option_text = item.option_text
            option.is_correct = option.id == correct_id
    else:
        for option in old_options.values():
            option.is_correct = option.id == correct_id
    if payload.question_text is not None:
        if not payload.question_text.strip():
            raise HTTPException(status_code=422, detail="Question text cannot be empty.")
        question.question_text = payload.question_text
    if payload.explanation is not None:
        question.explanation = payload.explanation
    question.correct_option_id = correct_id
    question.updated_at = datetime.utcnow()

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
        "image_url": question.image_url,
        "paper_set": question.paper_set,
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
        meta = json.loads(paper.meta or "{}")
        return {"status": "failed", "progress": 0, "step": meta.get("processing_error", "Processing failed. Please upload a valid PDF or DOCX.")}

    mem_progress = progress_info.get("progress", 0)
    mem_step = progress_info.get("step", "")
    if not mem_progress and paper.status == "processing":
        return {"status": "failed", "progress": 0,
                "step": "Processing was interrupted by a server restart. This upload is unchanged; please upload again."}

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
    if paper.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return paper


@router.get("/{paper_id}/assets/{filename}")
async def get_question_asset(paper_id: int, filename: str,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_owned_paper(paper_id, current_user.id, db)
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Image not found")
    image_url = f"/api/papers/{paper_id}/assets/{filename}"
    found = (await db.execute(select(Question.id).where(Question.paper_id == paper_id, Question.image_url == image_url).limit(1))).first()
    if not found:
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(get_settings().upload_dir) / "questions" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image no longer available. This preview uses temporary storage.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, no-store"})

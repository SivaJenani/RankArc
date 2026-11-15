from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models.attempt import Attempt, AttemptAnswer
from app.models.paper import Paper
from app.models.question import Option, Question
from app.models.user import User
from app.schemas.attempts import (
    AnswerResultItem,
    AttemptHistory,
    AttemptRead,
    AttemptResult,
    AttemptSubmit,
)
from app.schemas.questions import OptionRead, QuestionRead

router = APIRouter(tags=["attempts"])


@router.post("/start/{paper_id}", status_code=status.HTTP_201_CREATED)
async def start_attempt(
    paper_id: int,
    paper_set: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new attempt and return attempt_id + questions (answers hidden).
    Optional query param ?paper_set=<label> to filter to a specific paper set.
    """
    # Verify paper exists
    paper_result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper: Paper | None = paper_result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    # Fetch questions (optionally filtered by set)
    stmt = select(Question).where(Question.paper_id == paper_id)
    if paper_set:
        stmt = stmt.where(Question.paper_set == paper_set)
    stmt = stmt.order_by(Question.question_number)
    q_result = await db.execute(stmt)
    questions = q_result.scalars().all()

    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Paper has no questions yet. Wait for processing to complete.",
        )

    # Create attempt
    attempt = Attempt(
        user_id=current_user.id,
        paper_id=paper_id,
        started_at=datetime.utcnow(),
        total_questions=len(questions),
        status="in_progress",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    # Build question list WITHOUT revealing correct answers
    questions_out: list[dict] = []
    for q in questions:
        opts_result = await db.execute(
            select(Option).where(Option.question_id == q.id).order_by(Option.label)
        )
        opts = opts_result.scalars().all()
        # Hide is_correct and correct_option_id
        safe_opts = [
            OptionRead(id=o.id, label=o.label, option_text=o.option_text, is_correct=False)
            for o in opts
        ]
        questions_out.append(
            {
                "id": q.id,
                "question_number": q.question_number,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "explanation": None,
                "correct_option_id": None,
                "image_url": q.image_url,
                "options": [o.model_dump() for o in safe_opts],
            }
        )

    return {
        "attempt_id": attempt.id,
        "paper_id": paper_id,
        "total_questions": len(questions),
        "started_at": attempt.started_at.isoformat(),
        "questions": questions_out,
        "duration_seconds": _get_duration_from_paper(paper),
    }


def _get_duration_from_paper(paper: Paper) -> int | None:
    """Extract duration_seconds from paper.meta if available."""
    if not paper.meta:
        return None
    try:
        meta = json.loads(paper.meta)
        mins = meta.get("duration_minutes")
        if mins:
            return int(mins) * 60
    except Exception:
        pass
    return None


@router.post("/{attempt_id}/submit", response_model=AttemptRead)
async def submit_attempt(
    attempt_id: int,
    payload: AttemptSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptRead:
    """Save all answers, calculate score, and mark the attempt as completed."""
    attempt = await _get_owned_attempt(attempt_id, current_user.id, db)

    if attempt.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attempt already submitted",
        )

    correct_count = 0

    for answer in payload.answers:
        # Fetch question to get the correct_option_id
        q_result = await db.execute(select(Question).where(Question.id == answer.question_id))
        question: Question | None = q_result.scalar_one_or_none()
        if not question:
            continue

        is_correct: bool | None = None
        if answer.selected_option_id is not None and question.correct_option_id is not None:
            is_correct = answer.selected_option_id == question.correct_option_id
            if is_correct:
                correct_count += 1

        attempt_answer = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=answer.question_id,
            selected_option_id=answer.selected_option_id,
            is_correct=int(is_correct) if is_correct is not None else None,
            time_spent_seconds=answer.time_spent_seconds,
        )
        db.add(attempt_answer)

    total = attempt.total_questions or len(payload.answers)
    score = (correct_count / total * 100) if total > 0 else 0.0

    attempt.score = score
    attempt.submitted_at = datetime.utcnow()
    attempt.status = "completed"
    attempt.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(attempt)
    return AttemptRead.model_validate(attempt)


@router.get("/{attempt_id}/result", response_model=AttemptResult)
async def get_attempt_result(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptResult:
    """Return score and per-question breakdown with correct answers revealed."""
    attempt = await _get_owned_attempt(attempt_id, current_user.id, db)

    if attempt.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Attempt has not been submitted yet.",
        )

    # Fetch all answers for this attempt
    aa_result = await db.execute(
        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
    )
    attempt_answers = aa_result.scalars().all()

    answer_items: list[AnswerResultItem] = []
    for aa in attempt_answers:
        q_result = await db.execute(select(Question).where(Question.id == aa.question_id))
        question: Question | None = q_result.scalar_one_or_none()
        if not question:
            continue

        opts_result = await db.execute(
            select(Option).where(Option.question_id == question.id).order_by(Option.label)
        )
        opts = opts_result.scalars().all()
        opts_read = [OptionRead.model_validate(o) for o in opts]

        answer_items.append(
            AnswerResultItem(
                question_id=question.id,
                question_text=question.question_text,
                selected_option_id=aa.selected_option_id,
                correct_option_id=question.correct_option_id,
                is_correct=bool(aa.is_correct) if aa.is_correct is not None else None,
                explanation=question.explanation,
                image_url=question.image_url,
                options=opts_read,
            )
        )

    return AttemptResult(
        attempt=AttemptRead.model_validate(attempt),
        answers=answer_items,
    )


@router.get("/history", response_model=list[AttemptHistory])
async def attempt_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AttemptHistory]:
    """List all past attempts for the current user, with paper title."""
    result = await db.execute(
        select(Attempt, Paper.title.label("paper_title"))
        .join(Paper, Paper.id == Attempt.paper_id)
        .where(Attempt.user_id == current_user.id)
        .order_by(Attempt.started_at.desc())
    )
    rows = result.all()
    return [
        AttemptHistory(
            id=attempt.id,
            paper_id=attempt.paper_id,
            paper_title=paper_title,
            score=attempt.score,
            total_questions=attempt.total_questions,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            status=attempt.status,
        )
        for attempt, paper_title in rows
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_owned_attempt(attempt_id: int, user_id: int, db: AsyncSession) -> Attempt:
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    attempt: Attempt | None = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    if attempt.user_id is None:
        attempt.user_id = user_id
        await db.commit()
    elif attempt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return attempt

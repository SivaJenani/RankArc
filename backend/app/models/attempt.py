from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Attempt(TimestampMixin, Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")

    user: Mapped["User"] = relationship("User", back_populates="attempts")  # type: ignore[name-defined]
    paper: Mapped["Paper"] = relationship("Paper", back_populates="attempts")  # type: ignore[name-defined]
    answers: Mapped[list["AttemptAnswer"]] = relationship(
        "AttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="select",
    )


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    selected_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("options.id"), nullable=True
    )
    is_correct: Mapped[bool | None] = mapped_column(Integer, nullable=True)
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="answers")
    question: Mapped["Question"] = relationship("Question")  # type: ignore[name-defined]
    selected_option: Mapped["Option"] = relationship("Option", foreign_keys=[selected_option_id])  # type: ignore[name-defined]

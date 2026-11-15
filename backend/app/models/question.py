from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    question_number: Mapped[int] = mapped_column(Integer)
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(20), default="mcq")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Which paper set this question belongs to (e.g. "2026-10-10 Shift 1")
    paper_set: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="questions")  # type: ignore[name-defined]
    options: Mapped[list["Option"]] = relationship(
        "Option",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Option.label",
    )


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    label: Mapped[str] = mapped_column(String(1))  # "A", "B", "C", "D"
    option_text: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped["Question"] = relationship("Question", back_populates="options")

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MarkingScheme(TimestampMixin, Base):
    __tablename__ = "marking_schemes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    section: Mapped[str] = mapped_column(String(80))
    question_type: Mapped[str] = mapped_column(String(40), default="single_choice")
    correct: Mapped[float] = mapped_column(Float)
    wrong: Mapped[float] = mapped_column(Float)
    unattempted: Mapped[float] = mapped_column(Float, default=0)
    attempt_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partial_marking_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="preset")

    exam = relationship("Exam")

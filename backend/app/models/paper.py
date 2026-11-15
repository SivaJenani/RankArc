from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PaperStatus(StrEnum):
    uploading = "uploading"
    processing = "processing"
    needs_review = "needs_review"
    ready = "ready"
    failed = "failed"
    archived = "archived"


class Paper(TimestampMixin, Base):
    __tablename__ = "papers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id"), index=True, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default=PaperStatus.uploading)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    answer_key_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(260), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # JSON blob: exam metadata detected from document (title, categories, sets, duration_minutes)
    meta: Mapped[str | None] = mapped_column(Text, nullable=True)

    exam = relationship("Exam", back_populates="papers", foreign_keys=[exam_id])
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="paper", lazy="select")
    attempts: Mapped[list["Attempt"]] = relationship("Attempt", back_populates="paper", lazy="select")

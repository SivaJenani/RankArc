from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(200), nullable=True)

    attempts: Mapped[list["Attempt"]] = relationship("Attempt", back_populates="user", lazy="select")

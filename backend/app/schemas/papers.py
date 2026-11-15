from datetime import datetime

from pydantic import BaseModel


class PaperCreate(BaseModel):
    title: str


class PaperRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    filename: str | None = None
    status: str
    created_at: datetime
    question_count: int = 0

from datetime import datetime

from pydantic import BaseModel

from app.schemas.questions import OptionRead


class AttemptCreate(BaseModel):
    paper_id: int


class AttemptRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    paper_id: int
    started_at: datetime
    submitted_at: datetime | None = None
    score: float | None = None
    total_questions: int
    status: str


class AnswerSubmit(BaseModel):
    question_id: int
    selected_option_id: int | None = None
    time_spent_seconds: int | None = None


class AttemptSubmit(BaseModel):
    answers: list[AnswerSubmit]


class AnswerResultItem(BaseModel):
    question_id: int
    question_text: str
    selected_option_id: int | None = None
    correct_option_id: int | None = None
    is_correct: bool | None = None
    explanation: str | None = None
    image_url: str | None = None
    options: list[OptionRead] = []


class AttemptResult(BaseModel):
    attempt: AttemptRead
    answers: list[AnswerResultItem]


class AttemptHistory(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    paper_id: int
    paper_title: str
    score: float | None = None
    total_questions: int
    started_at: datetime
    submitted_at: datetime | None = None
    status: str

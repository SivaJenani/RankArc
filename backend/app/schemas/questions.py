from pydantic import BaseModel


class OptionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    label: str
    option_text: str
    is_correct: bool
    image_url: str | None = None


class OptionUpdate(BaseModel):
    id: int | None = None
    label: str
    option_text: str
    is_correct: bool
    image_url: str | None = None


class QuestionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    question_number: int
    question_text: str
    question_type: str
    explanation: str | None = None
    correct_option_id: int | None = None
    image_url: str | None = None
    paper_set: str | None = None
    options: list[OptionRead] = []


class QuestionUpdate(BaseModel):
    question_text: str | None = None
    explanation: str | None = None
    correct_option_id: int | None = None
    image_url: str | None = None
    options: list[OptionUpdate] | None = None

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class DataCreate(BaseModel):
    date: date
    value: float = Field(ge=0, allow_inf_nan=False)
    memo: str = Field(default="", max_length=500)


class DataUpdate(BaseModel):
    value: float = Field(ge=0, allow_inf_nan=False)
    memo: str = Field(default="", max_length=500)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class ConversationCreate(BaseModel):
    title: str = Field(default="새 대화", max_length=80)
    messages: list[Message] = Field(default_factory=list, max_length=30)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=100)


class DataRecord(DataCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)

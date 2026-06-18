"""Request/response schemas."""
from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Turn] = Field(default_factory=list)


class Explainability(BaseModel):
    source_name: str
    data_source: str
    query_timestamp: str
    sql: str | None = None
    execution_ms: int | None = None
    confidence: str = "medium"


class ChatResponse(BaseModel):
    answer: str
    explainability: Explainability
    rows: list[dict] | None = None

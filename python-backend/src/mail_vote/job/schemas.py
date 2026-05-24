"""求职分析模块的 Pydantic 模型。"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class JobPredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="邮件正文")
    subject: str = Field(default="", description="邮件主题")


class EntityResult(BaseModel):
    company: List[str] = Field(default_factory=list)
    position: List[str] = Field(default_factory=list)
    time: List[str] = Field(default_factory=list)
    round: List[str] = Field(default_factory=list)
    location: List[str] = Field(default_factory=list)


class JobPredictResponse(BaseModel):
    is_job: bool
    confidence: float
    stage: Optional[str] = None
    stage_confidence: Optional[float] = None
    entities: EntityResult = Field(default_factory=EntityResult)


class JobFeedbackRequest(BaseModel):
    email_id: int
    correct_is_job: Optional[bool] = None
    correct_stage: Optional[str] = None
    correct_entities: Optional[Dict[str, List[str]]] = None


class JobFeedbackResponse(BaseModel):
    status: str = "saved"
    email_id: int

"""FastAPI / Java 对接用 Pydantic 模型。"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="邮件全文（建议 Subject 与 Body 拼接）")
    mode: Literal["soft", "hard"] = "soft"
    fusion_weight_sklearn_stage1: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="覆盖阶段一 soft 融合：w×sklearn + (1-w)×TextCNN；省略则用 meta.json",
    )
    fusion_weight_sklearn_stage2: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="覆盖阶段二 soft 融合；省略则用 meta.json",
    )


class PredictResponse(BaseModel):
    stage1_label: str
    stage1_index: int
    final: str
    stage2_label: Optional[str] = None
    stage2_index: Optional[int] = None
    effective_fusion_weight_stage1: float = Field(
        ...,
        description="本次请求实际使用的阶段一 sklearn 权重（已裁剪到 [0,1]）",
    )
    effective_fusion_weight_stage2: float = Field(
        ...,
        description="本次请求实际使用的阶段二 sklearn 权重",
    )


class EvaluateItem(BaseModel):
    id: Optional[str] = Field(default=None, description="可选业务主键")
    text: str = Field(..., min_length=1)
    gold_stage1: str = Field(..., description="ham 或 spam")
    gold_stage2: Optional[str] = Field(default=None, description="spam 时留空；ham 时为细类")
    note_zh: Optional[str] = Field(default=None)


class EvaluateBatchRequest(BaseModel):
    items: List[EvaluateItem] = Field(..., min_length=1, max_length=2000)
    mode: Literal["soft", "hard"] = "soft"
    include_reports: bool = Field(default=False, description="是否返回 sklearn 文本报告")
    fusion_weight_sklearn_stage1: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="批量评估时统一覆盖阶段一融合权重"
    )
    fusion_weight_sklearn_stage2: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="批量评估时统一覆盖阶段二融合权重"
    )


class HealthResponse(BaseModel):
    status: str
    artifact_root: str
    stage1_class_names: List[str]
    stage2_class_names: List[str]
    fusion_weight_sklearn_stage1: float = Field(
        ..., description="当前阶段一产物 meta 中的 fusion_weight_sklearn（训练时 --fusion-w 写入）"
    )
    fusion_weight_sklearn_stage2: float = Field(..., description="当前阶段二产物 meta 中的 fusion_weight_sklearn")


class ErrorBody(BaseModel):
    detail: str

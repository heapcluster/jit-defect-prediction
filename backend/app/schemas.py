"""Pydantic 响应模型：让 OpenAPI/Swagger 携带响应字段，供镜像比对（tasks 5.1）。"""

from __future__ import annotations

from pydantic import BaseModel


class ExplanationItem(BaseModel):
    feature: str
    contribution: float
    direction: str


class CommitItem(BaseModel):
    commit_hash: str
    author_name: str
    committed_at: str
    message: str
    risk_score: float
    model_name: str


class CommitsData(BaseModel):
    total: int
    page: int
    size: int
    items: list[CommitItem]


class CommitsResponse(BaseModel):
    code: int
    message: str
    data: CommitsData


class DetailData(BaseModel):
    commit_hash: str
    author_name: str
    committed_at: str
    message: str
    risk_score: float | None
    model_name: str | None
    features: dict[str, float | int] | None
    explanation: list[ExplanationItem]


class DetailResponse(BaseModel):
    code: int
    message: str
    data: DetailData


class SeriesItem(BaseModel):
    period: str
    commit_count: int
    avg_risk: float
    high_risk_count: int


class TrendsData(BaseModel):
    granularity: str
    model_name: str | None
    series: list[SeriesItem]


class TrendsResponse(BaseModel):
    code: int
    message: str
    data: TrendsData


class PredictData(BaseModel):
    commit_hash: str
    model_name: str
    risk_score: float
    predicted_at: str
    features: dict[str, float | int]
    explanation: list[ExplanationItem]


class PredictResponse(BaseModel):
    code: int
    message: str
    data: PredictData

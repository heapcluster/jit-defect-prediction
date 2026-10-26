"""Pydantic 响应模型：让 OpenAPI/Swagger 携带响应字段，供镜像比对（tasks 5.1）。"""

from __future__ import annotations

from pydantic import BaseModel


class ExplanationItem(BaseModel):
    feature: str
    contribution: float
    direction: str
    # 因子中文名（app.explain.FEATURE_LABELS）；未知因子回退原名
    label: str = ""


class LabelData(BaseModel):
    """人工反馈标签（feedback capability）：`label_method="manual"` 的那一行。"""

    commit_hash: str
    is_defect: bool
    labeled_at: str | None


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
    label: LabelData | None = None


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


class SyncPrsSkippedItem(BaseModel):
    """sync_prs 的跳过条目：fetch 失败与单提交预测失败两种形态，字段并集。"""

    pr: int
    reason: str | None = None
    commit: str | None = None
    code: int | None = None
    message: str | None = None


class SyncPrsPrItem(BaseModel):
    pr: int
    title: str
    commits_predicted: int


class SyncPrsData(BaseModel):
    prs_scanned: int
    commits_predicted: int
    prs: list[SyncPrsPrItem]
    skipped: list[SyncPrsSkippedItem]


class SyncPrsResponse(BaseModel):
    code: int
    message: str
    data: SyncPrsData


class PrListItem(BaseModel):
    number: int
    title: str
    author: str
    state: str
    html_url: str
    updated_at: str
    risk_score: float | None
    risk_level: str | None = None
    reason: str | None = None
    commit_count: int
    predicted_count: int
    predicted_at: str | None


class PrsData(BaseModel):
    items: list[PrListItem]
    model_name: str
    skipped: int


class PrsResponse(BaseModel):
    code: int
    message: str
    data: PrsData


class PrCommitItem(BaseModel):
    sha: str
    message: str
    author: str
    risk_score: float | None
    risk_level: str | None = None
    predicted_at: str | None


class PrDetailData(BaseModel):
    number: int
    title: str
    author: str
    state: str
    html_url: str
    updated_at: str
    model_name: str
    commits: list[PrCommitItem]


class PrDetailResponse(BaseModel):
    code: int
    message: str
    data: PrDetailData


class LabelResponse(BaseModel):
    code: int
    message: str
    data: LabelData


class HealthData(BaseModel):
    """健康检查与运行状态（observability capability）。"""

    status: str
    db: str
    models_loaded: int
    model_names: list[str]
    commit_count: int
    prediction_count: int
    labeled_count: int
    last_sync_at: str | None
    server_time: str


class HealthResponse(BaseModel):
    code: int
    message: str
    data: HealthData

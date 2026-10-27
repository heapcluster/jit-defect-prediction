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


class QualityData(BaseModel):
    """人工标签 vs 预测的质量指标（change quality-loop）。分母为 0 时指标为 null。"""

    model_name: str | None
    threshold: float
    labeled_total: int
    evaluated: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float | None
    recall: float | None
    f1: float | None
    accuracy: float | None
    avg_risk_defect: float | None
    avg_risk_clean: float | None
    recommended_threshold: float | None
    evaluated_at: str


class QualityResponse(BaseModel):
    code: int
    message: str
    data: QualityData


class QualityDatasetItem(BaseModel):
    commit_hash: str
    is_defect: bool
    labeled_at: str | None
    committed_at: str | None
    features: dict[str, float | int] | None


class QualityDatasetData(BaseModel):
    count: int
    items: list[QualityDatasetItem]


class QualityDatasetResponse(BaseModel):
    code: int
    message: str
    data: QualityDatasetData


class ThresholdStats(BaseModel):
    threshold: float
    precision: float | None
    recall: float | None
    f1: float | None


class CalibrateData(BaseModel):
    model_name: str | None
    labeled_total: int
    evaluated: int
    applied: bool
    reason: str | None
    before: ThresholdStats
    after: ThresholdStats


class CalibrateResponse(BaseModel):
    code: int
    message: str
    data: CalibrateData


class ConfigData(BaseModel):
    """运行时配置（change ops-hardening）：阈值热更新，改完立即生效。"""

    high_risk_threshold: float
    mid_risk_threshold: float
    sync_initial_limit: int
    sync_catchup_limit: int
    updated_at: str | None


class ConfigResponse(BaseModel):
    code: int
    message: str
    data: ConfigData


class ConfigUpdateRequest(BaseModel):
    high_risk_threshold: float
    mid_risk_threshold: float


class LiveData(BaseModel):
    """liveness：只证明进程活着（不查 DB，DB 挂不该导致重启）。"""

    status: str
    server_time: str


class LiveResponse(BaseModel):
    code: int
    message: str
    data: LiveData


class ReadyData(BaseModel):
    """readiness：DB 通 + 模型已加载才算就绪。"""

    status: str
    db: str
    models_loaded: int
    server_time: str


class ReadyResponse(BaseModel):
    code: int
    message: str
    data: ReadyData


class GateData(BaseModel):
    """CI 风险门禁结果：`blocked=true` 时 CI 应阻断合并。"""

    number: int
    model_name: str
    risk_score: float | None
    risk_level: str | None
    threshold: float
    blocked: bool
    reason: str | None


class GateResponse(BaseModel):
    code: int
    message: str
    data: GateData


class WebhookData(BaseModel):
    """GitHub webhook 受理结果：`triggered` 表示是否真的派发了后台同步。"""

    accepted: bool
    event: str | None
    action: str | None
    triggered: bool


class WebhookResponse(BaseModel):
    code: int
    message: str
    data: WebhookData

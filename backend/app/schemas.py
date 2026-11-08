"""Pydantic 响应模型：让 OpenAPI/Swagger 携带响应字段，供镜像比对。

口径对齐 docs/api/*（commits / models / predict / sync / trends / figures / health）；
PR、质量、反馈、运行时配置等已下线模块的 schema 一并删除。
"""

from __future__ import annotations

from pydantic import BaseModel


class ExplanationItem(BaseModel):
    feature: str
    contribution: float
    direction: str
    # 因子中文名（app.explain.FEATURE_LABELS）；未知因子回退原名
    label: str = ""


class LocalizationHighlight(BaseModel):
    """缺陷定位的高亮项：按 |SHAP contribution| 降序的可疑特征。"""

    feature: str
    label: str
    contribution: float
    direction: str


class LocalizationLine(BaseModel):
    """新增代码行（可疑行）：行号 + 内容。"""

    number: int
    content: str


class LocalizationFile(BaseModel):
    path: str
    added_lines: list[LocalizationLine]


class Localization(BaseModel):
    """缺陷可视化定位（G1-1）。

    有历史仓库可解析 diff 时 level="line"（按提交级缺陷概率着色新增行）；
    否则 level="commit"（SHAP 特征归因）。MUST NOT 编造行级概率。
    """

    level: str
    notice: str
    highlights: list[LocalizationHighlight]
    files: list[LocalizationFile] = []
    truncated: bool = False


class FixReferenceItem(BaseModel):
    commit_hash: str
    message: str
    committed_at: str


class FixReferences(BaseModel):
    """高质量修复参考（G1-2）：同仓库历史修复提交；无依据时 items 为空。"""

    basis: str
    items: list[FixReferenceItem]


class CommitItem(BaseModel):
    commit_hash: str
    author_name: str
    committed_at: str
    message: str
    risk_score: float
    model_name: str
    # 仅 with_features=1 时返回：Kamei 14 维 log 变换值（可负）
    features: dict[str, float | int] | None = None
    # SZZ 真标签：1 / 0 / null（未打标）
    is_bug_inducing: int | None = None


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
    predicted_at: str | None
    features: dict[str, float | int] | None
    explanation: list[ExplanationItem]
    is_bug_inducing: int | None = None
    localization: Localization | None = None
    fix_references: FixReferences | None = None


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


class ModelsLineData(BaseModel):
    line: str
    label: str
    models: list[str]


class ModelsData(BaseModel):
    lines: list[ModelsLineData]


class ModelsResponse(BaseModel):
    code: int
    message: str
    data: ModelsData


class FigureData(BaseModel):
    figure_type: str
    title: str
    file_path: str


class MetricsData(BaseModel):
    auc: float
    ap: float
    f1: float
    precision: float
    recall: float
    accuracy: float
    n: int
    pos_rate: float


class FiguresData(BaseModel):
    model_name: str
    line: str
    metrics: MetricsData | None = None
    figures: list[FigureData]


class FiguresResponse(BaseModel):
    code: int
    message: str
    data: FiguresData


class HealthData(BaseModel):
    """健康检查与运行状态（observability capability）。"""

    status: str
    db: str
    models_loaded: int
    model_names: list[str]
    commit_count: int
    prediction_count: int
    last_sync_at: str | None
    server_time: str


class HealthResponse(BaseModel):
    code: int
    message: str
    data: HealthData


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

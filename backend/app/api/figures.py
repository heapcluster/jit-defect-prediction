"""模型性能图与指标接口：GET /api/figures（docs/api/figures.md）。

图清单来自 `model_figure` 登记；指标只读同批次 §3.6 evaluate_metrics 长表，
指标键以 `data_model/evaluation/metrics.py` 注册表为单源。本接口不重算指标、
不生成图、不写文件；缺图/校验失败进 missing，不作为 50000。
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from app import config, schemas
from app.api.storage import query_keys
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Model, ModelFigure
from app.services import evaluate_run, output_store
from app.services import file_contracts as fc

router = APIRouter(dependencies=[Depends(require_api_key)])

# 图集固定展示顺序（docs/api/figures.md）
_FIGURE_ORDER = ("roc", "pr", "confusion", "calibration", "effort", "feat_importance")
# §3.6 指标长表列序，逐字段投影，不重算
_METRIC_COLUMNS = (
    "model_name", "line", "metric", "value", "threshold", "n", "pos_rate",
    "dataset_version", "model_version", "computed_at",
)
_FLOAT_FIELDS = ("value", "threshold", "pos_rate")
_INT_FIELDS = ("n",)
_JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
_QUERY_PARAMS = {"model_name", "figure_type", "job_id"}


def _message(error: AppError) -> str:
    return str(getattr(error, "message", error))


def _output_ref(file_path: str) -> tuple[str, str] | None:
    """从 `temp/outputs/<job_id>/<name>` 解析 (job_id, name)。"""
    prefix = config.OUTPUTS_REL + "/"
    if not file_path.startswith(prefix):
        return None
    parts = file_path[len(prefix):].split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return parts[0], parts[1]


def _figure_state(file_path: str) -> tuple[Path | None, str | None]:
    """定位登记图文件；输出批次走登记校验（含 checksum），静态根拒绝越界路径。"""
    reference = _output_ref(file_path)
    if reference is not None:
        try:
            return output_store.read_output("storage", *reference), None
        except AppError as error:
            reason = "checksum_mismatch" if "checksum" in _message(error) else "file_missing"
            return None, reason
    prefix = "/static/"
    if not file_path.startswith(prefix):
        return None, "invalid_path"
    relative = Path(file_path[len(prefix):])
    if relative.is_absolute() or ".." in relative.parts:
        return None, "invalid_path"
    local = config.FIGURES_DIR.parent / relative
    if not local.is_file():
        return None, "file_missing"
    return local, None


def _figure_checksum(path: Path) -> tuple[str | None, str | None]:
    """PNG 魔数 + SHA-256；伪造格式与真图同等对待，不冒充可用 URL。"""
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "file_unreadable"
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return None, "invalid_png"
    return fc.sha256(raw), None


def _effort_kind(row: ModelFigure, file_path: str) -> str | None:
    """非 effort 图为 null；effort 图从登记名/标题识别 aware/unaware，无法证明则留 null。"""
    if row.figure_type != "effort":
        return None
    text = f"{Path(file_path).name} {row.title}".lower()
    if "unaware" in text:
        return "unaware"
    if "aware" in text:
        return "aware"
    return None


def _metric_file(job_id: str) -> tuple[Path | None, str | None]:
    """按批次取已登记的 §3.6 指标文件；checksum 不符与文件缺失分开说明。"""
    if not _JOB_ID.fullmatch(job_id):
        return None, "invalid_job_id"
    reason = "metrics_file_missing"
    for name in (f"evaluate_metrics_{job_id}.csv", f"evaluate_metrics_{job_id}.xlsx"):
        try:
            return output_store.read_output("evaluate", job_id, name), None
        except AppError as error:
            if "checksum" in _message(error):
                reason = "metrics_checksum_mismatch"
    return None, reason


def _project_metric(raw: dict) -> dict:
    row = {column: raw.get(column) for column in _METRIC_COLUMNS}
    for field in _FLOAT_FIELDS:
        if row[field] not in (None, ""):
            try:
                row[field] = float(row[field])
            except (TypeError, ValueError):
                pass
    for field in _INT_FIELDS:
        if row[field] not in (None, ""):
            try:
                row[field] = int(row[field])
            except (TypeError, ValueError):
                pass
    return row


def _discover_job(model_name: str) -> str | None:
    """缺省批次：该模型有指标行且 manifest 完整的最新 evaluate 批次。"""
    root = output_store.OUTPUT_ROOT
    if not root.is_dir():
        return None
    candidates: list[tuple[str, str]] = []
    for directory in root.iterdir():
        job_id = directory.name
        if directory.is_symlink() or not directory.is_dir() or not _JOB_ID.fullmatch(job_id):
            continue
        index_path = directory / ".index.json"
        try:
            index = output_store.read_json(index_path.read_bytes())
        except (OSError, AppError):
            continue
        if index.get("module") != "evaluate" or index.get("job_id") != job_id:
            continue
        manifest_name = index.get("manifest_name")
        if not isinstance(manifest_name, str):
            continue
        manifest_path = directory / manifest_name
        if manifest_path.is_symlink() or not manifest_path.is_file():
            continue
        try:
            created = str(output_store.read_json(manifest_path.read_bytes()).get("created_at") or "")
        except (OSError, AppError):
            continue
        path, _ = _metric_file(job_id)
        if path is None:
            continue
        try:
            _, rows = fc.read_table(path.name, path.read_bytes())
        except (OSError, AppError):
            continue
        if not any((row.get("model_name") or "").strip() == model_name for row in rows):
            continue
        candidates.append((created, job_id))
    return sorted(candidates, reverse=True)[0][1] if candidates else None


def _load_metrics(model_name: str, job_id: str | None) -> tuple[list[dict], str | None, str | None]:
    """返回 (metrics, unavailable_reason, source_job_id)；只读投影，不重算任何数值。"""
    resolved = job_id or _discover_job(model_name)
    if not resolved:
        return [], "evaluate_batch_missing", None
    path, reason = _metric_file(resolved)
    if path is None:
        return [], reason, resolved
    try:
        columns, rows = fc.read_table(path.name, path.read_bytes())
    except (OSError, AppError):
        return [], "metrics_file_unreadable", resolved
    if not set(_METRIC_COLUMNS) <= set(columns):
        return [], "metrics_schema_mismatch", resolved
    selected = [
        _project_metric(row)
        for row in rows
        if (row.get("model_name") or "").strip() == model_name
    ]
    if not selected:
        return [], "model_metrics_missing", resolved
    # 指标名以当前注册表为单源，历史批次里的非注册指标不冒充当前指标。
    registered = set(evaluate_run._metrics().metric_keys())
    selected = [row for row in selected if row["metric"] in registered]
    if not selected:
        return [], "metrics_not_in_registry", resolved
    return selected, None, resolved


@router.get("/api/figures", response_model=schemas.FiguresResponse)
def figures(
    request: Request,
    model_name: str | None = Query(default=None),
    figure_type: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
) -> dict:
    query_keys(request, _QUERY_PARAMS)
    if figure_type is not None and figure_type not in _FIGURE_ORDER:
        raise AppError(40001, "参数非法：figure_type 取值不在契约图类型内")
    with SessionLocal() as session:
        model = session.execute(
            select(Model).where(Model.model_name == model_name)
        ).scalar_one_or_none()
        rows = (
            session.execute(select(ModelFigure).where(ModelFigure.model_name == model_name))
            .scalars()
            .all()
        )
    if model is None or not rows:
        raise AppError(40400, "model figures not found")
    by_type = {row.figure_type: row for row in rows}
    metrics, metrics_unavailable, resolved_job = _load_metrics(model_name, job_id)

    figures_list: list[dict] = []
    missing: list[dict] = []
    for kind in ((figure_type,) if figure_type else _FIGURE_ORDER):
        row = by_type.get(kind)
        if row is None:
            continue
        local, reason = _figure_state(row.file_path)
        if local is None:
            missing.append({"figure_type": kind, "file_path": row.file_path, "reason": reason})
            continue
        checksum, reason = _figure_checksum(local)
        if checksum is None:
            missing.append({"figure_type": kind, "file_path": row.file_path, "reason": reason})
            continue
        reference = _output_ref(row.file_path)
        public_path = (
            f"/api/storage/outputs/{reference[0]}/{reference[1]}"
            if reference is not None
            else row.file_path
        )
        figures_list.append({
            "figure_type": kind,
            "effort_kind": _effort_kind(row, row.file_path),
            "title": row.title,
            "file_path": public_path,
            "checksum_sha256": checksum,
            "source_job_id": reference[0] if reference is not None else None,
        })

    data = {
        "model_name": model_name,
        "line": model.line,
        "source_job_id": job_id or resolved_job or (
            figures_list[0]["source_job_id"] if figures_list else None
        ),
        "metrics": metrics,
        "metrics_unavailable": metrics_unavailable,
        "figures": figures_list,
        "missing": missing,
    }
    return ok(data)

"""运行时配置：阈值热更新（change ops-hardening）。

为什么单独开 `/api/config` 而不是继续用 `.env`：阈值是运营参数，改一次重启一次
就没法跟质量看板的校准联动。写入走 `runtime_setting`，读走内存缓存，改完立即生效。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import config, model_registry, schemas
from app.auth import require_api_key
from app.errors import AppError, ok
from app.services import settings as runtime_settings

router = APIRouter(dependencies=[Depends(require_api_key)])


def _snapshot() -> dict:
    thresholds = runtime_settings.thresholds()
    return {
        "high_risk_threshold": thresholds[runtime_settings.HIGH_KEY],
        "mid_risk_threshold": thresholds[runtime_settings.MID_KEY],
        "champion_model": runtime_settings.champion_model(),
        # 同步限额只读：改动涉及批处理规模，仍归 .env
        "sync_initial_limit": config.SYNC_INITIAL_LIMIT,
        "sync_catchup_limit": config.SYNC_CATCHUP_LIMIT,
        "updated_at": runtime_settings.updated_at(),
    }


@router.get("/api/config", response_model=schemas.ConfigResponse)
def get_config() -> dict:
    return ok(_snapshot())


@router.put("/api/config", response_model=schemas.ConfigResponse)
def put_config(body: schemas.ConfigUpdateRequest) -> dict:
    """更新风险等级阈值与冠军模型；阈值约束 `0 <= mid <= high <= 1`，非法 → 40001。

    `champion_model` 必须是已加载的模型名（不在清单内 → 40001）；传空字符串表示清除，
    回到「version_key 最大者」兜底口径。
    """
    if body.champion_model:
        if not model_registry.has(body.champion_model):
            raise AppError(40001, "参数非法：champion_model 不在已加载模型清单")
    runtime_settings.set_thresholds(high=body.high_risk_threshold, mid=body.mid_risk_threshold)
    if body.champion_model is not None:
        runtime_settings.set_champion_model(body.champion_model or None)
    return ok(_snapshot())

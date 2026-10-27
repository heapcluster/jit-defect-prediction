"""运行时配置：阈值热更新（change ops-hardening）。

为什么单独开 `/api/config` 而不是继续用 `.env`：阈值是运营参数，改一次重启一次
就没法跟质量看板的校准联动。写入走 `runtime_setting`，读走内存缓存，改完立即生效。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import config, schemas
from app.auth import require_api_key
from app.errors import ok
from app.services import settings as runtime_settings

router = APIRouter(dependencies=[Depends(require_api_key)])


def _snapshot() -> dict:
    thresholds = runtime_settings.thresholds()
    return {
        "high_risk_threshold": thresholds[runtime_settings.HIGH_KEY],
        "mid_risk_threshold": thresholds[runtime_settings.MID_KEY],
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
    """更新风险等级阈值；约束 `0 <= mid <= high <= 1`，非法 → 40001。"""
    runtime_settings.set_thresholds(high=body.high_risk_threshold, mid=body.mid_risk_threshold)
    return ok(_snapshot())

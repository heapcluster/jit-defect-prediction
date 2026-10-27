"""同步状态快照共享服务（供 sync / health 等模块复用）。

此前 `_sync_state` / `_sync_lock` / `get_sync_state` 定义在 `app.api.sync`，
`health.snapshot()` 需通过 `app.api.sync` 跨路由导入，层次被破坏。
本模块统一为唯一定义点，对外行为与原实现一字不变。
"""

from __future__ import annotations

import threading

# 同步状态快照（实时可见）：前端 SSE 订阅；首启/手动/追到 HEAD 共用
_sync_state: dict = {
    "running": False,
    "mode": None,  # "startup" | "manual" | "catchup"
    "scope": None,  # "baseline" | "catchup-to-head" | "latest"
    "total": 0,
    "done": 0,
    "current_hash": None,
    "started_at": None,
    "last_error": None,
}

_sync_lock = threading.Lock()


def set_state(**kwargs) -> None:
    for k, v in kwargs.items():
        if k in _sync_state:
            _sync_state[k] = v


def get_sync_state() -> dict:
    return dict(_sync_state)

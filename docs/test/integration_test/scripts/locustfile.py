"""Locust 压测脚本（新版考核说明 §4.1 的性能测试交付物之一）。

本机未安装 locust，按要求不安装；此文件供具备 Locust 的环境复跑：

    pip install locust   # 仅在允许安装的环境执行
    locust -f backend/scripts/locustfile.py --host http://127.0.0.1:8000
    # Web UI 设置 users / spawn-rate，记录并发用户数、响应时间、吞吐量、错误率

等价的零依赖压测可直接跑 `python scripts/load_test.py`。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from locust import HttpUser, between, task
except ImportError:  # 未安装 locust 时不影响仓库其他脚本
    HttpUser = object
    between = lambda *_: None  # noqa: E731
    task = lambda *_: lambda f: f  # noqa: E731

API_TOKEN = os.getenv("API_TOKEN", "")


class PredictUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        self.client.headers.update({"X-API-Key": API_TOKEN})
        data = self.client.get("/api/commits", params={"size": 1}).json()["data"]["items"][0]
        self.payload = {"commit_hash": data["commit_hash"], "model_name": data["model_name"]}

    @task(5)
    def predict(self) -> None:
        self.client.post("/api/predict", json=self.payload, name="POST /api/predict")

    @task(1)
    def list_commits(self) -> None:
        self.client.get("/api/commits", params={"size": 20}, name="GET /api/commits")

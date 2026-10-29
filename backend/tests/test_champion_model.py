"""冠军模型（缺陷 D2）：全站默认模型单一定义点。

验收要点：
1. 未配置 champion_model → 回退 version_key 最大者（design D6），不报错；
2. 配置后列表与详情同时切换，且同一提交两处分数逐字相等（此前详情会按可用行另取模型）；
3. 非法模型名 → 40001 且不写入；
4. 传空字符串 → 清除配置，回到 version_key 兜底。
"""

from datetime import datetime

from app import model_registry
from app.db import SessionLocal
from app.models import Prediction

from tests.conftest import C1, C2, HEADERS

# conftest 的 client 夹具预置了 fixture_v2 的两条预测；测试交付清单里另有 fixture_v1 / fixture_v2，
# 其中 fixture_v2 才是 version_key 最大者 → 用它验证「冠军可覆盖 version_key 兜底」。
XGB = "fixture_v2"
LR = "fixture_v1"


def _seed_prediction(commit_hash: str, model_name: str, score: str) -> None:
    with SessionLocal() as session:
        session.add(
            Prediction(
                commit_hash=commit_hash,
                model_name=model_name,
                risk_score=score,
                predicted_at=datetime(2026, 9, 2, 8, 0, 0),
                feature_version="v1",
            )
        )
        session.commit()


def _put_config(client, **overrides):
    body = {"high_risk_threshold": 0.5, "mid_risk_threshold": 0.2}
    body.update(overrides)
    return client.put("/api/config", json=body, headers=HEADERS)


def test_default_model_falls_back_to_version_key_max(client):
    data = client.get("/api/commits", headers=HEADERS).json()["data"]
    assert data["total"] == 2
    assert {item["model_name"] for item in data["items"]} == {XGB}


def test_champion_switch_moves_list_and_detail_together(client):
    # 同一条提交同时存在两个模型的预测，且分数不同——这正是此前「列表与详情不同分」的场景
    _seed_prediction(C1, LR, "0.41000")
    _seed_prediction(C2, LR, "0.90000")
    assert model_registry.has(LR), "fixture_v1 必须在交付清单里，否则该用例无法验证冠军切换"

    resp = _put_config(client, champion_model=LR)
    assert resp.status_code == 200
    assert resp.json()["data"]["champion_model"] == LR

    listed = client.get("/api/commits", headers=HEADERS).json()["data"]
    assert {item["model_name"] for item in listed["items"]} == {LR}
    # 列表按风险降序：C2(0.90) 在 C1(0.41) 之前
    assert [item["commit_hash"] for item in listed["items"]] == [C2, C1]

    for item in listed["items"]:
        detail = client.get(f"/api/commits/{item['commit_hash']}", headers=HEADERS).json()["data"]
        assert detail["model_name"] == item["model_name"] == LR
        assert detail["risk_score"] == item["risk_score"]


def test_invalid_champion_is_40001_and_not_written(client):
    resp = _put_config(client, champion_model="not_delivered_v9")
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001
    # 未写入：仍是 version_key 兜底的 fixture_v2
    data = client.get("/api/config", headers=HEADERS).json()["data"]
    assert data["champion_model"] is None


def test_empty_champion_clears_back_to_version_key(client):
    assert _put_config(client, champion_model=LR).status_code == 200
    assert _put_config(client, champion_model="").status_code == 200
    data = client.get("/api/config", headers=HEADERS).json()["data"]
    assert data["champion_model"] is None
    listed = client.get("/api/commits", headers=HEADERS).json()["data"]
    assert {item["model_name"] for item in listed["items"]} == {XGB}


def test_predict_uses_champion_model(client):
    """单条预测的默认模型与列表/详情同源：配置 champion 后不得再回落到 version_key 最大者。"""
    _seed_prediction(C1, LR, "0.41000")
    assert _put_config(client, champion_model=LR).status_code == 200

    body = client.post("/api/predict", json={"commit_hash": C1}, headers=HEADERS).json()
    assert body["code"] == 0
    assert body["data"]["model_name"] == LR

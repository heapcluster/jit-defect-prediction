"""预测质量与标签回流（change quality-loop）测试。

覆盖：混淆矩阵与派生指标、无标签/标签无预测两类边界、回流样本导出、
阈值校准（落库 + 即时生效 + 样本不足不写入）。
"""

from __future__ import annotations

from app.services import settings as runtime_settings

from tests.conftest import C1, C2, C3, HEADERS


def _label(client, commit_hash: str, is_defect: bool) -> None:
    resp = client.put(
        f"/api/commits/{commit_hash}/label", json={"is_defect": is_defect}, headers=HEADERS
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0


def test_quality_metrics_with_labels(client):
    """C1(0.8732, 缺陷) + C2(0.21, 非缺陷)，阈值 0.5 → 完美分类。"""
    _label(client, C1, True)
    _label(client, C2, False)

    body = client.get(
        "/api/quality", params={"model_name": "xgb_v1", "threshold": 0.5}, headers=HEADERS
    ).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["labeled_total"] == 2
    assert data["evaluated"] == 2
    assert (data["tp"], data["fp"], data["tn"], data["fn"]) == (1, 0, 1, 0)
    assert data["precision"] == 1.0
    assert data["recall"] == 1.0
    assert data["f1"] == 1.0
    assert data["accuracy"] == 1.0


def test_quality_without_labels_returns_zero_and_null(client):
    """无标签：evaluated=0，派生指标为 null（不得用 0 冒充完美）。"""
    body = client.get("/api/quality", headers=HEADERS).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["labeled_total"] == 0
    assert data["evaluated"] == 0
    assert data["precision"] is None
    assert data["recall"] is None
    assert data["f1"] is None
    assert data["recommended_threshold"] is None


def test_quality_label_without_prediction_counts_in_total_only(client):
    """C3 无 prediction：计入 labeled_total，不计入 evaluated。"""
    _label(client, C3, True)
    body = client.get("/api/quality", params={"model_name": "xgb_v1"}, headers=HEADERS).json()
    assert body["data"]["labeled_total"] == 1
    assert body["data"]["evaluated"] == 0


def test_quality_dataset_exports_labels_with_features(client):
    _label(client, C1, True)
    _label(client, C3, False)

    body = client.get("/api/quality/dataset", headers=HEADERS).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["count"] == 2
    by_hash = {item["commit_hash"]: item for item in data["items"]}
    assert by_hash[C1]["is_defect"] is True
    assert set(by_hash[C1]["features"]) == {
        "ns",
        "nd",
        "nf",
        "entropy",
        "la",
        "ld",
        "lt",
        "fix",
        "ndev",
        "age",
        "nuc",
        "exp",
        "rexp",
        "sexp",
    }
    # C3 没有 commit_feature：features 为 null，不得返回空 dict 冒充
    assert by_hash[C3]["features"] is None


def test_calibrate_applies_threshold_and_takes_effect(client):
    """当前阈值 0.9 明显过高（F1 为 null）→ 校准应下调并立即影响等级判定。"""
    runtime_settings.set_thresholds(high=0.9, mid=0.9)
    _label(client, C1, True)
    _label(client, C2, False)

    from app.services.settings import high_threshold

    assert high_threshold() == 0.9

    body = client.post(
        "/api/quality/calibrate", json={"model_name": "xgb_v1"}, headers=HEADERS
    ).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["evaluated"] == 2
    assert data["applied"] is True
    assert data["reason"] is None
    assert data["after"]["f1"] == 1.0
    # 校准后阈值立即生效（无需重启）：等级判定确实吃的是新阈值而非 .env 的 0.9
    new_high = high_threshold()
    assert new_high < 0.9

    from app.api.prs import get_pr_risk_level

    assert get_pr_risk_level(new_high) == "高"
    assert get_pr_risk_level(round(new_high - 0.05, 2)) != "高"


def test_calibrate_with_insufficient_labels_does_not_write(client):
    _label(client, C1, True)
    before = runtime_settings.high_threshold()

    body = client.post("/api/quality/calibrate", json={}, headers=HEADERS).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["applied"] is False
    assert data["reason"] == "insufficient_labels"
    assert runtime_settings.high_threshold() == before


def test_quality_rejects_invalid_threshold(client):
    body = client.get("/api/quality", params={"threshold": 1.5}, headers=HEADERS).json()
    assert body["code"] == 40001


def test_quality_requires_api_key(client):
    resp = client.get("/api/quality")
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_false_discovery_rate_is_complement_of_precision(client):
    """FDR = fp/(tp+fp) = 1 - precision；不是 fp/(fp+tn) 的 FPR。

    C1(0.8732) 判高但人工说非缺陷 → fp；C2(0.21) 判低但人工说是缺陷 → fn。
    """
    _label(client, C1, False)
    _label(client, C2, True)
    data = client.get(
        "/api/quality", params={"model_name": "xgb_v1", "threshold": 0.5}, headers=HEADERS
    ).json()["data"]
    assert (data["tp"], data["fp"], data["tn"], data["fn"]) == (0, 1, 0, 1)
    assert data["precision"] == 0.0
    assert data["false_discovery_rate"] == 1.0
    assert "false_positive_rate" not in data, "字段名已统一为 FDR，旧名不得回流"


def test_quality_rejects_invalid_label_source(client):
    resp = client.get("/api/quality", params={"label_source": "manual2"}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_szz_label_source_is_separate_from_manual(client):
    """label_source=szz 只统计 SZZ 标签：只有人工标签时该视图无样本。"""
    _label(client, C1, True)
    data = client.get(
        "/api/quality", params={"model_name": "xgb_v1", "label_source": "szz"}, headers=HEADERS
    ).json()["data"]
    assert data["label_source"] == "szz"
    assert data["labeled_total"] == 0
    assert data["evaluated"] == 0

"""人工反馈闭环（feedback capability）：PUT /api/commits/{commit_hash}/label。

覆盖 specs/feedback/spec.md 的 Scenario：标记 / 撤销 / commit 不存在 / 参数非法，
以及详情可见与列表按标签过滤；另含 explain 中文名的单元断言（query-api）。
"""

from app.explain import explain_label

from tests.conftest import C1, C2, HEADERS, UNKNOWN


def test_put_label_marks_commit_as_defect(client):
    resp = client.put(f"/api/commits/{C1}/label", json={"is_defect": True}, headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["commit_hash"] == C1
    assert body["data"]["is_defect"] is True
    assert body["data"]["labeled_at"].endswith("Z")

    detail = client.get(f"/api/commits/{C1}", headers=HEADERS).json()["data"]
    assert detail["label"]["is_defect"] is True
    assert detail["label"]["labeled_at"].endswith("Z")


def test_put_label_false_marks_confirmed_clean(client):
    """`is_defect=false` = 确认非缺陷（保留标签行，会计入质量指标 tn/fp）。"""
    client.put(f"/api/commits/{C1}/label", json={"is_defect": True}, headers=HEADERS)
    resp = client.put(f"/api/commits/{C1}/label", json={"is_defect": False}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_defect"] is False
    detail = client.get(f"/api/commits/{C1}", headers=HEADERS).json()["data"]
    assert detail["label"]["is_defect"] is False


def test_put_label_null_revokes_and_deletes_label(client):
    """`is_defect=null` 才是撤销：删除 manual 标签行，详情回到未标注。"""
    client.put(f"/api/commits/{C1}/label", json={"is_defect": True}, headers=HEADERS)
    resp = client.put(f"/api/commits/{C1}/label", json={"is_defect": None}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["is_defect"] is None
    assert data["labeled_at"] is None

    detail = client.get(f"/api/commits/{C1}", headers=HEADERS).json()["data"]
    assert detail["label"] is None, "撤销后 MUST 回到未标注，而不是留下「已确认非缺陷」"


def test_put_label_null_on_unlabeled_commit_is_idempotent(client):
    resp = client.put(f"/api/commits/{C2}/label", json={"is_defect": None}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_defect"] is None


def test_put_label_unknown_commit_returns_40400(client):
    resp = client.put(f"/api/commits/{UNKNOWN}/label", json={"is_defect": True}, headers=HEADERS)
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 40400
    assert body["data"] is None


def test_put_label_missing_is_defect_returns_40001(client):
    resp = client.put(f"/api/commits/{C1}/label", json={}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_put_label_invalid_hash_returns_40001(client):
    resp = client.put("/api/commits/not-a-hash/label", json={"is_defect": True}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_detail_label_is_null_when_unlabeled(client):
    detail = client.get(f"/api/commits/{C2}", headers=HEADERS).json()["data"]
    assert detail["label"] is None, "未标记 MUST NOT 返回占位空对象"


def test_list_commits_has_label_filter_only_returns_labeled(client):
    client.put(f"/api/commits/{C1}/label", json={"is_defect": True}, headers=HEADERS)
    body = client.get("/api/commits", params={"has_label": True}, headers=HEADERS).json()
    assert body["code"] == 0
    hashes = [item["commit_hash"] for item in body["data"]["items"]]
    assert C1 in hashes
    assert C2 not in hashes, "未标记的 C2 不应出现在 has_label=true 的过滤结果里"


def test_explain_label_known_and_unknown():
    assert explain_label("la") == "代码改动量大"
    # 未知因子回退原名，MUST NOT 报错
    assert explain_label("foo") == "foo"


def test_detail_explanation_items_carry_chinese_label(client):
    data = client.get(f"/api/commits/{C1}", headers=HEADERS).json()["data"]
    for item in data["explanation"]:
        assert "label" in item
        assert item["label"], "解释项 MUST 带非空中文名"

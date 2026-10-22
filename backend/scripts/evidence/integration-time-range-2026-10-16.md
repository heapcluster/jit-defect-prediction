# 时间区间语义联调证据 2026-10-16

- 目的：change `backend-time-range-semantics` 的**集成测试层**证据（`openspec/changes/archive/2026-10-21-backend-time-range-semantics/tasks.md`「测试与验证」§2；本行路径随归档移动更新）——真起服务、真发 HTTP 请求，**不用 TestClient**
- 被测：分支 `fix/backend/time-range-closed` head `9073cea`（PR #62），基线 main `59ad7ed`
- 环境：Windows 11 / Python 3.12.7 / 仓库 `.venv` / uvicorn 0.53.0 / fastapi 0.141.1 / SQLAlchemy 2.0.54 + **SQLite** 种子库（本轮不起 MySQL）
- 数据：cwd=`backend`，`python -m scripts.seed_dev_data` → 3 提交（`committed_at` = 2026-08-01 / 08-02 / 08-03 各 09:00:00）、3 特征、3 预测（`model_name=seed_v1`，`risk_score` 0.1 / 0.2 / 0.3）
- 服务：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8010`；鉴权头 `X-API-Key: dev-token-20260918`（开发令牌，与前端 `docs/frontend/integration-log.md` 同值 —— 该记录随 PR #60 已进 main；真实值只进各自 `.env` / `.env.local`，不入库）
- 结果：**11 / 11 全部符合预期**（逐条原始响应见 §3）

## 1. 断言表（预期 → 实际）

| # | 请求（均带 `X-API-Key`） | 预期 | 实际 | 结论 |
|---|---|---|---|---|
| A | 全区间纯日期：`start_time=2026-08-01&end_time=2026-08-03` | 含结束日全天 → `total=3`（3 条都在） | `code=0`、`total=3`、含 `committed_at=2026-08-03T09:00:00Z` | ✅ |
| B | 结束日前移一天：`end_time=2026-08-02` | `total=2`（区间语义没有放宽成「多给一天」） | `code=0`、`total=2` | ✅ |
| C | end 带时间分量：`end_time=2026-08-03T08:59:59` | 按原样解析，不含当天 09:00 → `total=2` | `code=0`、`total=2` | ✅ |
| D | **周下钻 W31**：`start_time=2026-07-27&end_time=2026-08-02`（周一→周日） | `total=2`（修复前只有 1，丢周日当天 = Issue #61 原现象） | `code=0`、`total=2` | ✅ |
| E | 紧凑基本格式：`end_time=20260803` | HTTP 400 + `code=40001`，message 指参数名 | 400 / `40001` / message 含 `end_time` 与合法写法 | ✅ |
| F | 紧凑 + Z 后缀：`end_time=20260803T090000Z` | 同 E（不被 `fromisoformat` 静默收下） | 400 / `40001` | ✅ |
| G | 趋势周粒度同区间：`granularity=week&start_time=2026-07-27&end_time=2026-08-03` | `2026-W31:2` + `2026-W32:1`，和 = A 的 `total` | `series=[(2026-W31,2),(2026-W32,1)]`，和 3 == A 的 3 | ✅ |
| H | 趋势周粒度只到 W31 末：`end_time=2026-08-02` | `2026-W31:2`，与 D 的下钻结果一致 | `series=[(2026-W31,2)]` == D 的 2 | ✅ |
| I | 趋势月粒度：`granularity=month&start_time=2026-08-01&end_time=2026-08-03` | `2026-08:3`（月桶不丢结束日） | `series=[(2026-08,3)]` | ✅ |
| J | 详情 API-02：`/api/commits/000...001` | `code=0` + 14 项 `features` | `code=0`、`features` 14 项、`risk_score=0.1`、`explanation=[]`（见 §5） | ✅ |
| K | 无 `X-API-Key` 打列表 | HTTP 401 + `code=40100` | 401 / `40100` / `missing or invalid token` | ✅ |

## 2. 关键跨接口一致性（本 change 的核心风险点）

| 断言 | 左值 | 右值 | 结论 |
|---|---|---|---|
| 列表与趋势同区间条数一致 | A `total=3` | G 周桶 `2026-W31:2 + 2026-W32:1 = 3` | ✅ 相等 |
| **周下钻不丢周日**（Issue #61 的原始现象） | D `total=2` | H `2026-W31:2` | ✅ 相等；修复前 D 只返回 1 条 |
| 月桶不丢结束日 | I `2026-08:3` | A `total=3` | ✅ 相等 |
| 收尾规则不外溢到 start / 显式时间 | B `total=2`、C `total=2` | 种子数据里 08-03 只有 09:00 一条 | ✅ 未多收 |

> 结论：契约 v1.5 的「闭区间 + 纯日期串 end 含全天 + 紧凑格式拒收」在真服务上成立，且**列表 / 趋势 / 周下钻 / 月桶四个口径互相对得上**——这正是 #61 里「趋势周下钻每周丢 1/7、与看板 `commit_count` 对不上」要消除的现象。

## 3. 原始响应（verbatim，未截断字段）

### A 全区间纯日期 end=08-03（期望 total=3，含 08-03 09:00）

```
GET /api/commits?start_time=2026-08-01&end_time=2026-08-03&size=10
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 3,
    "page": 1,
    "size": 10,
    "items": [
      {
        "commit_hash": "0000000000000000000000000000000000000003",
        "author_name": "seed-author-3",
        "committed_at": "2026-08-03T09:00:00Z",
        "message": "seed commit 3",
        "risk_score": 0.3,
        "model_name": "seed_v1"
      },
      {
        "commit_hash": "0000000000000000000000000000000000000002",
        "author_name": "seed-author-2",
        "committed_at": "2026-08-02T09:00:00Z",
        "message": "seed commit 2",
        "risk_score": 0.2,
        "model_name": "seed_v1"
      },
      {
        "commit_hash": "0000000000000000000000000000000000000001",
        "author_name": "seed-author-1",
        "committed_at": "2026-08-01T09:00:00Z",
        "message": "seed commit 1",
        "risk_score": 0.1,
        "model_name": "seed_v1"
      }
    ]
  }
}
HTTP_STATUS 200
```

### B end=08-02（期望 total=2）

```
GET /api/commits?start_time=2026-08-01&end_time=2026-08-02&size=10
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 2,
    "page": 1,
    "size": 10,
    "items": [
      {
        "commit_hash": "0000000000000000000000000000000000000002",
        "author_name": "seed-author-2",
        "committed_at": "2026-08-02T09:00:00Z",
        "message": "seed commit 2",
        "risk_score": 0.2,
        "model_name": "seed_v1"
      },
      {
        "commit_hash": "0000000000000000000000000000000000000001",
        "author_name": "seed-author-1",
        "committed_at": "2026-08-01T09:00:00Z",
        "message": "seed commit 1",
        "risk_score": 0.1,
        "model_name": "seed_v1"
      }
    ]
  }
}
HTTP_STATUS 200
```

### C end 带时间分量 08-03T08:59:59（期望 total=2，不含 09:00）

```
GET /api/commits?end_time=2026-08-03T08:59:59&size=10
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 2,
    "page": 1,
    "size": 10,
    "items": [
      {
        "commit_hash": "0000000000000000000000000000000000000002",
        "author_name": "seed-author-2",
        "committed_at": "2026-08-02T09:00:00Z",
        "message": "seed commit 2",
        "risk_score": 0.2,
        "model_name": "seed_v1"
      },
      {
        "commit_hash": "0000000000000000000000000000000000000001",
        "author_name": "seed-author-1",
        "committed_at": "2026-08-01T09:00:00Z",
        "message": "seed commit 1",
        "risk_score": 0.1,
        "model_name": "seed_v1"
      }
    ]
  }
}
HTTP_STATUS 200
```

### D 周下钻 W31：start=2026-07-27 end=2026-08-02（期望 total=2；修复前只有 1）

```
GET /api/commits?start_time=2026-07-27&end_time=2026-08-02&size=10
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 2,
    "page": 1,
    "size": 10,
    "items": [
      {
        "commit_hash": "0000000000000000000000000000000000000002",
        "author_name": "seed-author-2",
        "committed_at": "2026-08-02T09:00:00Z",
        "message": "seed commit 2",
        "risk_score": 0.2,
        "model_name": "seed_v1"
      },
      {
        "commit_hash": "0000000000000000000000000000000000000001",
        "author_name": "seed-author-1",
        "committed_at": "2026-08-01T09:00:00Z",
        "message": "seed commit 1",
        "risk_score": 0.1,
        "model_name": "seed_v1"
      }
    ]
  }
}
HTTP_STATUS 200
```

### E 紧凑基本格式 end=20260803（期望 400 + 40001）

```
GET /api/commits?end_time=20260803
{
  "code": 40001,
  "message": "参数非法：end_time 不接受紧凑基本格式，请用 YYYY-MM-DD 或带分隔符的 ISO 8601",
  "data": null
}
HTTP_STATUS 400
```

### F 紧凑带 Z end_time=20260803T090000Z（期望 400 + 40001）

```
GET /api/commits?end_time=20260803T090000Z
{
  "code": 40001,
  "message": "参数非法：end_time 不接受紧凑基本格式，请用 YYYY-MM-DD 或带分隔符的 ISO 8601",
  "data": null
}
HTTP_STATUS 400
```

### G 趋势 周粒度 同区间（期望 W31=2 + W32=1，和=3 与 A 一致）

```
GET /api/trends?granularity=week&start_time=2026-07-27&end_time=2026-08-03
{
  "code": 0,
  "message": "ok",
  "data": {
    "granularity": "week",
    "model_name": "seed_v1",
    "series": [
      {
        "period": "2026-W31",
        "commit_count": 2,
        "avg_risk": 0.15,
        "high_risk_count": 0
      },
      {
        "period": "2026-W32",
        "commit_count": 1,
        "avg_risk": 0.3,
        "high_risk_count": 0
      }
    ]
  }
}
HTTP_STATUS 200
```

### H 趋势 周粒度 只到 W31 末（期望 W31=2，与 D 一致）

```
GET /api/trends?granularity=week&start_time=2026-07-27&end_time=2026-08-02
{
  "code": 0,
  "message": "ok",
  "data": {
    "granularity": "week",
    "model_name": "seed_v1",
    "series": [
      {
        "period": "2026-W31",
        "commit_count": 2,
        "avg_risk": 0.15,
        "high_risk_count": 0
      }
    ]
  }
}
HTTP_STATUS 200
```

### I 趋势 月粒度（期望 2026-08 count=3）

```
GET /api/trends?granularity=month&start_time=2026-08-01&end_time=2026-08-03
{
  "code": 0,
  "message": "ok",
  "data": {
    "granularity": "month",
    "model_name": "seed_v1",
    "series": [
      {
        "period": "2026-08",
        "commit_count": 3,
        "avg_risk": 0.2,
        "high_risk_count": 0
      }
    ]
  }
}
HTTP_STATUS 200
```

### J 详情 API-02（期望 code=0 + 14 项 features）

```
GET /api/commits/0000000000000000000000000000000000000001
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "0000000000000000000000000000000000000001",
    "author_name": "seed-author-1",
    "committed_at": "2026-08-01T09:00:00Z",
    "message": "seed commit 1",
    "risk_score": 0.1,
    "model_name": "seed_v1",
    "features": {
      "ns": 1.0986,
      "nd": 1.6094,
      "nf": 1.9459,
      "entropy": 1.42,
      "la": -4.272,
      "ld": -5.2753,
      "lt": 7.1136,
      "fix": 1,
      "ndev": 1.3863,
      "age": 2.5257,
      "nuc": 0.2513,
      "exp": 5.7683,
      "rexp": 3.8114,
      "sexp": 2.8904
    },
    "explanation": []
  }
}
HTTP_STATUS 200
```

### K 无令牌（期望 HTTP 401 + 40100）

```
GET /api/commits
{
  "code": 40100,
  "message": "missing or invalid token",
  "data": null
}
HTTP_STATUS 401
```

## 4. 复现步骤（任何人照做）

```bash
# cwd = 仓库根下 backend/；临时库放仓库外，避免误入库
export DATABASE_URL="sqlite:///$TEMP/jit_int_62.db"
export API_TOKEN="dev-token-20260918"
python -m scripts.seed_dev_data                      # 期望：seed 数据写入完成（3 提交 / 3 特征 / 3 预测）
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 &
curl -s -H "X-API-Key: dev-token-20260918" \
  "http://127.0.0.1:8010/api/commits?start_time=2026-08-01&end_time=2026-08-03&size=10"
# 期望：total=3（含 committed_at=2026-08-03T09:00:00Z 的那条）
curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: dev-token-20260918" \
  "http://127.0.0.1:8010/api/commits?end_time=20260803"
# 期望：400
```

## 5. 边界与本轮不覆盖（如实登记）

1. 本轮是**后端侧**集成验证（真 HTTP + 真服务 + SQLite 种子）；执行时 #62 尚未合入，故在 PR 分支 head `9073cea` 上跑（该 head 已于 2026-10-16 07:49 原样合入 main `7844f8e`，接口代码逐字相同）。**三页面端到端 + 录屏**待与刘帅华、蒋励在 main 上一起走，其中 `docs/frontend/integration-log.md` 里标 ⏳ 的「日期末秒」项现在可按 main 复核改判，见 tasks.md §5 缺口表。
2. 未起真 MySQL：`prediction(commit_hash, model_name)` 唯一索引下的并发双插回落分支（`backend/app/api/predict.py:70-80`）与 `app/db.py` 的索引自检仍未覆盖，已登记 Issue #73。
3. J 项 `explanation` 为空数组属**预期**：`seed_v1` 只是种子预测行，`MODEL_DIR` 下没有同名模型文件；真模型的解释链路由 #52 的 `backend/tests/test_model_registry.py::test_explain_linear_pipeline` / `::test_explain_random_forest` / `::test_explain_linear_pipeline_shap_additivity` 覆盖（含 SHAP 可加性判据），与前端 `docs/frontend/integration-log.md` 的 API-02 记录一致。
4. 本文件只记已发生的验证；未做的一律写进上一条与 tasks.md §5，不倒填。

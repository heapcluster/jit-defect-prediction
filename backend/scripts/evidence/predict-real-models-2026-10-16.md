# API-04 在线预测证据（真交付模型）2026-10-16

- 目的：给 `POST /api/predict`（契约三 v1.5 §4）留一份**真模型 + 真服务**的端到端实跑记录。此前仓库里只有单测层证据（`backend/tests/test_model_registry.py`，#52）与压测/安全证据，没有一份「三个交付模型都能出分且 SHAP 解释非空」的可复现记录；前端 API-04 联调与 10/23 演示都以此为预期值基准。
- 被测：main `0cad776`（含 #62 的 v1.5 语义与 #52 的解释链路修复），后端代码与本仓库当前 `backend/app/` 一致
- 环境：Windows 11 / Python **3.12.7**（仓库根 `.venv`）/ fastapi 0.141.1 / uvicorn 0.53.0 / sqlalchemy 2.0.54 / scikit-learn 1.9.1 / xgboost 3.4.1 / shap 0.52.0 / joblib 1.6.0 —— 与模型交付包 `[dependencies]` 段钉的版本一致
- 模型来源：模型线 2026-09-20 交付包（Issue #39 已签收），`MODEL_DIR` 直接指向包内 `models/`；md5 与包内 `md5sums.txt` 一致：`lr_v1.pkl` `789d57c1a1ad492fa3204a44695e89ce`、`rf_v1.pkl` `71731a270b679dc74b4006ba68c7856f`、`xgb_v1.pkl` `c436197daa4bccda9a08a60748e0107b`。**模型文件不入库**（`.gitignore` 第 14–15 行 `*.pkl` / `*.joblib`），故本文件只记 md5 与结果，不含模型本体
- 数据：cwd=`backend`，`python -m scripts.seed_dev_data` → 3 提交 / 3 特征 / 3 预测（`committed_at` 2026-08-01..03 各 09:00，特征为契约二 14 项、`feature_version=v1`，预测行 `model_name=seed_v1`）
- 服务：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8011`；`DATABASE_URL` 指仓库外 SQLite 文件、`API_TOKEN=dev-token-20260918`（开发令牌，走环境变量/`.env`，不入库）
- 启动自检：日志 `INFO:backend.model_registry:loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']` —— 三个模型全部通过加载期特征数自检（`n_features_in_` / `booster.num_features()` == 14，Issue #46/#47 的防线），无 `model skipped`、无 `model load failed`
- 结果：**15 / 15 全部符合预期**（5 条正向 + 4 条异常 + 6 条缺省来源对照 L0–L4），原始响应 verbatim 见 §3

## 1. 断言表（预期 → 实际）

| # | 请求 | 预期 | 实际 | 结论 |
|---|---|---|---|---|
| P1 | `{"commit_hash":"000…0001"}`（不带 `model_name`） | 缺省取**版本序最大**模型 = `xgb_v1`（`version_key`，design D6） | 200 / `code=0` / `model_name=xgb_v1` / `risk_score=0.54026` / `features` 14 项 / `explanation` 14 项（increase 7、decrease 7） | ✅ |
| P2 | 同上 + `"model_name":"xgb_v1"` | 与 P1 逐值相同（缺省解析到的就是它） | 200 / `risk_score=0.54026`，top3 `nf +0.779282` / `lt +0.752006` / `sexp −0.58849` | ✅ |
| P3 | `"model_name":"lr_v1"`（`Pipeline(StandardScaler→LogisticRegression)`） | 线性模型走 LinearExplainer，解释非空且**不重复折算**（#52 修的点） | 200 / `risk_score=0.71587` / `explanation` 14 项（increase 8、decrease 6），top3 `ns −1.316359` / `nd +1.275347` / `sexp +1.205397` | ✅ |
| P4 | `"model_name":"rf_v1"`（随机森林） | shap 0.52 对森林返回三维数组，`_first_row` 取 `[:, :, 1]` 后仍是 14 项（#52 修的另一点） | 200 / `risk_score=0.57964` / `explanation` 14 项，top3 `sexp −0.090127` / `nf +0.082635` / `nd +0.071295` | ✅ |
| P5 | P2 原样再打一次 | 幂等：同 `commit_hash`+`model_name` **只保留最新一行**（upsert，不新增） | 200 / `risk_score=0.54026` 与 P2 一致；随后列表查 `xgb_v1` 仍只有 1 行（见「落库核对」） | ✅ |
| E1 | `commit_hash` 39 位 | 400 + `40001`，message 说明需 40 位十六进制 | 400 / `40001` / `参数非法：commit_hash 需为 40 位十六进制` | ✅ |
| E2 | `commit_hash` 合法 40 位但库里没有（`ffff…`） | 404 + `40400` | 404 / `40400` / `commit not found` | ✅ |
| E3 | `"model_name":"seed_v1"`（库里有该预测行、但注册表无此模型） | 400 + `40001`（枚举值不存在走 40001，**不是** 50000） | 400 / `40001` / `参数非法：model_name 不在已加载模型清单` | ✅ |
| E4 | 不带 `X-API-Key` | 401 + `40100` | 401 / `40100` / `missing or invalid token` | ✅ |
| L0 | 真模型已加载、**尚未 POST**：`GET /api/commits?size=10`（不带 `model_name`） | 列表缺省模型取**prediction 表**内版本序最大者（`default_model_in_table`），表里只有 `seed_v1` → 仍 3 条 seed | 200 / `total=3` / `models={seed_v1}` —— **证明「加载模型」本身不改变列表** | ✅ |
| L0b | 同上 + `?model_name=seed_v1` | 显式指定表内模型 → 3 条 | 200 / `total=3` / `{seed_v1}` | ✅ |
| L0c | 同上 + `?model_name=xgb_v1`（注册表有、表里还没有它的预测行） | 列表按表过滤 → 0 条（不是报错） | 200 / `total=0` / `items=[]` | ✅ |
| L2 | P1 的 POST **之后**再打 L0 的请求 | 表里已有 `xgb_v1` 行且版本序最大 → 缺省切到 `xgb_v1`，只有被 predict 过的 1 条 | 200 / `total=1` / `{xgb_v1}` | ✅ |
| L3 | POST 之后 + `?model_name=seed_v1` | 种子 3 条仍在，只是不再是缺省 | 200 / `total=3` / `{seed_v1}` | ✅ |
| L4 | POST 之后 + `?model_name=xgb_v1` | 与 L2 一致 | 200 / `total=1` / `{xgb_v1}` | ✅ |

> L0–L4 是与 P1 同一次服务启动内的连续序列（L1 即 P1 那次 POST，不重复计行）；原始响应见 §3「缺省模型来源对照」。

## 2. 落库核对与一个必须知道的口径

- **幂等落库**：P5 复跑后查 `GET /api/commits?size=5` → `total=1`，仅 `("…0001", risk_score=0.54026, model_name=xgb_v1)` 一行 —— 同 `commit_hash`+`model_name` 只保留最新一行，没有因为打了两次就多出一行。
- **⚠ 两个「缺省模型」来源不同，切换时机也不同（前端联调必看，sober-hub 10-16 复审 P2 订正）**：
  - `GET /api/commits` / `GET /api/trends` 的缺省模型 = `backend/app/api/commits.py:50-53` 的 `default_model_in_table()` —— 查 **prediction 表** `distinct model_name` 后按 `version_key` 取最大，**与模型注册表里加载了什么无关**；
  - `POST /api/predict` 的缺省模型 = **模型注册表**版本序最大者（`model_registry.default_model()`）。
  - 因此正确因果是：**仅加载真模型不会改变列表**（L0：仍 `seed_v1` / 3 条）；**第一次 POST 成功、往 prediction 表写入 `xgb_v1` 行之后**，列表缺省才切到 `xgb_v1`，且 `items` 只取单个 `model_name` 的行 → 只剩被 predict 过的那 1 条（L2）；种子 3 条并未消失，显式 `?model_name=seed_v1` 仍全在（L3）。这不是缺陷，是契约三 §3「列表只取单模型 + 缺省取表内版本序最大」的既有语义。
  - 前端若「加载了模型就期待列表变化」会扑空；要真实规模的列表数据，须把模型线全量 `prediction_result.csv`（10,893 行 `xgb_v1`）连同 commits / features CSV 一起灌库（`python -m app.ingest <commits|labels|features|predictions> <csv>`），后三类 CSV 仓库内没有（数据线产物不入库），灌库仍待模型线交付。
- **解释非空**：三个模型的 `explanation` 都是 14 项、`direction` 有增有减，即提交详情页「为什么判为高风险」有内容可渲染（#50 / #52 的原缺陷是这里恒为空数组）。

## 3. 原始响应（verbatim）

### P1 缺省 model_name（应取版本序最大 = xgb_v1）

```
POST /api/predict  body={"commit_hash":"0000000000000000000000000000000000000001"}
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "0000000000000000000000000000000000000001",
    "model_name": "xgb_v1",
    "risk_score": 0.54026,
    "predicted_at": "2026-10-16T08:46:50.953346Z",
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
    "explanation": [
      {
        "feature": "ns",
        "contribution": 0.197487,
        "direction": "decrease"
      },
      {
        "feature": "nd",
        "contribution": 0.305042,
        "direction": "increase"
      },
      {
        "feature": "nf",
        "contribution": 0.779282,
        "direction": "increase"
      },
      {
        "feature": "entropy",
        "contribution": 0.196386,
        "direction": "decrease"
      },
      {
        "feature": "la",
        "contribution": 0.0834,
        "direction": "decrease"
      },
      {
        "feature": "ld",
        "contribution": 0.081617,
        "direction": "increase"
      },
      {
        "feature": "lt",
        "contribution": 0.752006,
        "direction": "increase"
      },
      {
        "feature": "fix",
        "contribution": 0.319197,
        "direction": "increase"
      },
      {
        "feature": "ndev",
        "contribution": 0.149947,
        "direction": "increase"
      },
      {
        "feature": "age",
        "contribution": 0.04632,
        "direction": "increase"
      },
      {
        "feature": "nuc",
        "contribution": 0.550589,
        "direction": "decrease"
      },
      {
        "feature": "exp",
        "contribution": 0.107721,
        "direction": "decrease"
      },
      {
        "feature": "rexp",
        "contribution": 0.49166,
        "direction": "decrease"
      },
      {
        "feature": "sexp",
        "contribution": 0.58849,
        "direction": "decrease"
      }
    ]
  }
}
HTTP_STATUS 200
```

### P2 指定 xgb_v1

```
POST /api/predict  body={"commit_hash":"0000000000000000000000000000000000000001","model_name":"xgb_v1"}
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "0000000000000000000000000000000000000001",
    "model_name": "xgb_v1",
    "risk_score": 0.54026,
    "predicted_at": "2026-10-16T08:46:51.120577Z",
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
    "explanation": [
      {
        "feature": "ns",
        "contribution": 0.197487,
        "direction": "decrease"
      },
      {
        "feature": "nd",
        "contribution": 0.305042,
        "direction": "increase"
      },
      {
        "feature": "nf",
        "contribution": 0.779282,
        "direction": "increase"
      },
      {
        "feature": "entropy",
        "contribution": 0.196386,
        "direction": "decrease"
      },
      {
        "feature": "la",
        "contribution": 0.0834,
        "direction": "decrease"
      },
      {
        "feature": "ld",
        "contribution": 0.081617,
        "direction": "increase"
      },
      {
        "feature": "lt",
        "contribution": 0.752006,
        "direction": "increase"
      },
      {
        "feature": "fix",
        "contribution": 0.319197,
        "direction": "increase"
      },
      {
        "feature": "ndev",
        "contribution": 0.149947,
        "direction": "increase"
      },
      {
        "feature": "age",
        "contribution": 0.04632,
        "direction": "increase"
      },
      {
        "feature": "nuc",
        "contribution": 0.550589,
        "direction": "decrease"
      },
      {
        "feature": "exp",
        "contribution": 0.107721,
        "direction": "decrease"
      },
      {
        "feature": "rexp",
        "contribution": 0.49166,
        "direction": "decrease"
      },
      {
        "feature": "sexp",
        "contribution": 0.58849,
        "direction": "decrease"
      }
    ]
  }
}
HTTP_STATUS 200
```

### P3 指定 lr_v1（Pipeline: StandardScaler+LogisticRegression）

```
POST /api/predict  body={"commit_hash":"0000000000000000000000000000000000000001","model_name":"lr_v1"}
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "0000000000000000000000000000000000000001",
    "model_name": "lr_v1",
    "risk_score": 0.71587,
    "predicted_at": "2026-10-16T08:46:51.255168Z",
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
    "explanation": [
      {
        "feature": "ns",
        "contribution": 1.316359,
        "direction": "decrease"
      },
      {
        "feature": "nd",
        "contribution": 1.275347,
        "direction": "increase"
      },
      {
        "feature": "nf",
        "contribution": 0.327647,
        "direction": "increase"
      },
      {
        "feature": "entropy",
        "contribution": 0.869918,
        "direction": "decrease"
      },
      {
        "feature": "la",
        "contribution": 0.847404,
        "direction": "decrease"
      },
      {
        "feature": "ld",
        "contribution": 0.167733,
        "direction": "decrease"
      },
      {
        "feature": "lt",
        "contribution": 0.941992,
        "direction": "increase"
      },
      {
        "feature": "fix",
        "contribution": 0.503225,
        "direction": "increase"
      },
      {
        "feature": "ndev",
        "contribution": 0.597873,
        "direction": "increase"
      },
      {
        "feature": "age",
        "contribution": 0.143168,
        "direction": "increase"
      },
      {
        "feature": "nuc",
        "contribution": 0.046411,
        "direction": "decrease"
      },
      {
        "feature": "exp",
        "contribution": 0.243573,
        "direction": "increase"
      },
      {
        "feature": "rexp",
        "contribution": 1.05673,
        "direction": "decrease"
      },
      {
        "feature": "sexp",
        "contribution": 1.205397,
        "direction": "increase"
      }
    ]
  }
}
HTTP_STATUS 200
```

### P4 指定 rf_v1（三维 SHAP 归一化路径）

```
POST /api/predict  body={"commit_hash":"0000000000000000000000000000000000000001","model_name":"rf_v1"}
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "0000000000000000000000000000000000000001",
    "model_name": "rf_v1",
    "risk_score": 0.57964,
    "predicted_at": "2026-10-16T08:46:51.551083Z",
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
    "explanation": [
      {
        "feature": "ns",
        "contribution": 0.017133,
        "direction": "decrease"
      },
      {
        "feature": "nd",
        "contribution": 0.071295,
        "direction": "increase"
      },
      {
        "feature": "nf",
        "contribution": 0.082635,
        "direction": "increase"
      },
      {
        "feature": "entropy",
        "contribution": 0.011646,
        "direction": "increase"
      },
      {
        "feature": "la",
        "contribution": 0.00532,
        "direction": "increase"
      },
      {
        "feature": "ld",
        "contribution": 0.004869,
        "direction": "decrease"
      },
      {
        "feature": "lt",
        "contribution": 0.038454,
        "direction": "increase"
      },
      {
        "feature": "fix",
        "contribution": 0.038817,
        "direction": "increase"
      },
      {
        "feature": "ndev",
        "contribution": 0.013063,
        "direction": "increase"
      },
      {
        "feature": "age",
        "contribution": 0.003658,
        "direction": "increase"
      },
      {
        "feature": "nuc",
        "contribution": 0.046867,
        "direction": "decrease"
      },
      {
        "feature": "exp",
        "contribution": 0.008117,
        "direction": "decrease"
      },
      {
        "feature": "rexp",
        "contribution": 0.004766,
        "direction": "decrease"
      },
      {
        "feature": "sexp",
        "contribution": 0.090127,
        "direction": "decrease"
      }
    ]
  }
}
HTTP_STATUS 200
```

### P5 幂等复跑（同 hash+model 再打一次，应只保留最新一行）

```
POST /api/predict  body={"commit_hash":"0000000000000000000000000000000000000001","model_name":"xgb_v1"}
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "0000000000000000000000000000000000000001",
    "model_name": "xgb_v1",
    "risk_score": 0.54026,
    "predicted_at": "2026-10-16T08:46:51.621141Z",
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
    "explanation": [
      {
        "feature": "ns",
        "contribution": 0.197487,
        "direction": "decrease"
      },
      {
        "feature": "nd",
        "contribution": 0.305042,
        "direction": "increase"
      },
      {
        "feature": "nf",
        "contribution": 0.779282,
        "direction": "increase"
      },
      {
        "feature": "entropy",
        "contribution": 0.196386,
        "direction": "decrease"
      },
      {
        "feature": "la",
        "contribution": 0.0834,
        "direction": "decrease"
      },
      {
        "feature": "ld",
        "contribution": 0.081617,
        "direction": "increase"
      },
      {
        "feature": "lt",
        "contribution": 0.752006,
        "direction": "increase"
      },
      {
        "feature": "fix",
        "contribution": 0.319197,
        "direction": "increase"
      },
      {
        "feature": "ndev",
        "contribution": 0.149947,
        "direction": "increase"
      },
      {
        "feature": "age",
        "contribution": 0.04632,
        "direction": "increase"
      },
      {
        "feature": "nuc",
        "contribution": 0.550589,
        "direction": "decrease"
      },
      {
        "feature": "exp",
        "contribution": 0.107721,
        "direction": "decrease"
      },
      {
        "feature": "rexp",
        "contribution": 0.49166,
        "direction": "decrease"
      },
      {
        "feature": "sexp",
        "contribution": 0.58849,
        "direction": "decrease"
      }
    ]
  }
}
HTTP_STATUS 200
```

### E1 hash 格式非法（39 位）

```
POST /api/predict  body={"commit_hash":"000000000000000000000000000000000000001"}
{
  "code": 40001,
  "message": "参数非法：commit_hash 需为 40 位十六进制",
  "data": null
}
HTTP_STATUS 400
```

### E2 commit 不存在（40 位合法但库里没有）

```
POST /api/predict  body={"commit_hash":"ffffffffffffffffffffffffffffffffffffffff"}
{
  "code": 40400,
  "message": "commit not found",
  "data": null
}
HTTP_STATUS 404
```

### E3 model_name 不在已加载清单

```
POST /api/predict  body={"commit_hash":"0000000000000000000000000000000000000001","model_name":"seed_v1"}
{
  "code": 40001,
  "message": "参数非法：model_name 不在已加载模型清单",
  "data": null
}
HTTP_STATUS 400
```

### E4 无令牌

```
POST /api/predict
{
  "code": 40100,
  "message": "missing or invalid token",
  "data": null
}
HTTP_STATUS 401
```

### 落库核对：`GET /api/commits?size=5`（P5 之后）

```
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 1,
    "page": 1,
    "size": 5,
    "items": [
      {
        "commit_hash": "0000000000000000000000000000000000000001",
        "author_name": "seed-author-1",
        "committed_at": "2026-08-01T09:00:00Z",
        "message": "seed commit 1",
        "risk_score": 0.54026,
        "model_name": "xgb_v1"
      }
    ]
  }
}
```

### 缺省模型来源对照（L0–L4：与 P1 同一次服务启动内的连续序列）

### L0 模型已加载、尚未 POST：缺省列表（期望 seed_v1 / 3 条）

```
GET /api/commits?size=10
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
### L0b 同上但显式 model_name=seed_v1（期望 3 条）

```
GET /api/commits?size=10&model_name=seed_v1
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
### L0c 显式 model_name=xgb_v1（期望 total=0：表里还没有它的预测行）

```
GET /api/commits?size=10&model_name=xgb_v1
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 0,
    "page": 1,
    "size": 10,
    "items": []
  }
}
HTTP_STATUS 200
```
### L1 POST /api/predict（缺省取注册表版本序最大 = xgb_v1）

```
body={"commit_hash":"0000000000000000000000000000000000000001"}
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "0000000000000000000000000000000000000001",
    "model_name": "xgb_v1",
    "risk_score": 0.54026,
    "predicted_at": "2026-10-16T13:24:37.684543Z",
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
    "explanation": [
      {
        "feature": "ns",
        "contribution": 0.197487,
        "direction": "decrease"
      },
      {
        "feature": "nd",
        "contribution": 0.305042,
        "direction": "increase"
      },
      {
        "feature": "nf",
        "contribution": 0.779282,
        "direction": "increase"
      },
      {
        "feature": "entropy",
        "contribution": 0.196386,
        "direction": "decrease"
      },
      {
        "feature": "la",
        "contribution": 0.0834,
        "direction": "decrease"
      },
      {
        "feature": "ld",
        "contribution": 0.081617,
        "direction": "increase"
      },
      {
        "feature": "lt",
        "contribution": 0.752006,
        "direction": "increase"
      },
      {
        "feature": "fix",
        "contribution": 0.319197,
        "direction": "increase"
      },
      {
        "feature": "ndev",
        "contribution": 0.149947,
        "direction": "increase"
      },
      {
        "feature": "age",
        "contribution": 0.04632,
        "direction": "increase"
      },
      {
        "feature": "nuc",
        "contribution": 0.550589,
        "direction": "decrease"
      },
      {
        "feature": "exp",
        "contribution": 0.107721,
        "direction": "decrease"
      },
      {
        "feature": "rexp",
        "contribution": 0.49166,
        "direction": "decrease"
      },
      {
        "feature": "sexp",
        "contribution": 0.58849,
        "direction": "decrease"
      }
    ]
  }
}
HTTP_STATUS 200
```
### L2 POST 之后：缺省列表（期望 xgb_v1 / 1 条）

```
GET /api/commits?size=10
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 1,
    "page": 1,
    "size": 10,
    "items": [
      {
        "commit_hash": "0000000000000000000000000000000000000001",
        "author_name": "seed-author-1",
        "committed_at": "2026-08-01T09:00:00Z",
        "message": "seed commit 1",
        "risk_score": 0.54026,
        "model_name": "xgb_v1"
      }
    ]
  }
}
HTTP_STATUS 200
```
### L3 POST 之后：显式 model_name=seed_v1（期望仍 3 条）

```
GET /api/commits?size=10&model_name=seed_v1
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
### L4 POST 之后：显式 model_name=xgb_v1（期望 1 条）

```
GET /api/commits?size=10&model_name=xgb_v1
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 1,
    "page": 1,
    "size": 10,
    "items": [
      {
        "commit_hash": "0000000000000000000000000000000000000001",
        "author_name": "seed-author-1",
        "committed_at": "2026-08-01T09:00:00Z",
        "message": "seed commit 1",
        "risk_score": 0.54026,
        "model_name": "xgb_v1"
      }
    ]
  }
}
HTTP_STATUS 200
```

## 4. 复现步骤（任何人照做，含前端联调方）

```bash
# 0) 先拿到模型：*.pkl 不入库，找模型线（蒋励）要 2026-09-20 交付包，或向后端线要副本；用包内 md5sums.txt 校验
#    md5sum -c md5sums.txt   → 三个 .pkl 均 OK
# 1) 依赖（版本必须与交付包 [dependencies] 一致，backend/requirements.txt 已是这套）
python -m pip install -r backend/requirements.txt
cd backend                                    # 以下命令一律在 backend/ 下执行（仓库根切进来）
# 2) 环境变量（.env 或 export 均可，SQLite 文件放仓库外避免误入库）
export DATABASE_URL="sqlite:///$TEMP/jit_predict04.db"
export API_TOKEN="dev-token-20260918"
export MODEL_DIR="<交付包路径>/models"      # 或把三个 .pkl 放进 data_model/models/ 后省略本行
# 3) 种子数据 + 起服务
python -m scripts.seed_dev_data            # 期望：3 提交 / 3 特征 / 3 预测
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
#    启动日志期望出现：loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']
# 4) 打 API-04（期望 risk_score=0.54026、explanation 14 项）
curl -s -X POST -H "X-API-Key: dev-token-20260918" -H "Content-Type: application/json" \
  -d '{"commit_hash":"0000000000000000000000000000000000000001"}' \
  http://127.0.0.1:8000/api/predict
# 5) 异常路径（期望依次 400/40001、404/40400、400/40001、401/40100）
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "X-API-Key: dev-token-20260918" \
  -H "Content-Type: application/json" -d '{"commit_hash":"ffffffffffffffffffffffffffffffffffffffff"}' \
  http://127.0.0.1:8000/api/predict
```

> `risk_score` 的小数位由后端按契约四舍五入到 5 位；同一模型 + 同一特征向量必须**逐值可复现**（P1/P2/P5 三次相同即为证）。若你跑出的分数与上表不同，先查三件事：模型 md5 是否一致、依赖版本是否被 pip 解析成了别的版本、`MODEL_DIR` 是否指到了别的目录。

## 5. 边界与本轮不覆盖（如实登记）

1. 本轮用 **SQLite 种子库**，不是真 MySQL：`prediction` 唯一索引下并发双插的 `IntegrityError` 回落分支（`backend/app/api/predict.py:70-80`）仍未覆盖，已登记 Issue #73。
2. 未做并发/压测：`POST /api/predict` 的性能证据是 `backend/scripts/evidence/perf-real-2026-09-20.md`（p95 21.6ms，真模型 xgb_v1），本轮不重跑。
3. 未用真实提交哈希：仓库内没有 commits / features 的全量 CSV（数据线产物不入库），故只能用种子哈希走链路；真实规模数据的端到端仍待灌库。
4. 前端三页面对 API-04 的渲染（详情页解释区、模型切换）由前端线在 `docs/frontend/integration-log.md` 自行记录，本文件只提供后端侧预期值，不代替前端实测。

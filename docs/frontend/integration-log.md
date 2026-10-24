# 前端联调记录（API-01/02/03 + 鉴权）

> change `frontend-integration` ｜ 前端线 刘帅华 ｜ 记录 2026-10-13
> 类型：本地真实后端联调（非 mock）；后端为 FastAPI + SQLite 种子数据

## 环境与启动

| 项 | 值 |
|---|---|
| 前端 SHA | `90ef424`（业务 head） |
| 环境 | Windows 11，Node 24，Python 3.12 |
| 后端启动 | `cd backend` → `python -m scripts.seed_dev_data`（seed 3 提交 / 3 特征 / 3 预测）→ `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| 鉴权配置 | 请求头 `X-API-Key`，值 `dev-token-20260918`（开发令牌，已脱敏；真实值只进各自 `.env.local`，不入库） |
| MODEL_DIR | 留空，回落 repo 内 `data_model/pipelines/expert/models/`（不写个人绝对路径） |

## 验证结果（预期 → 实际）

### API-01 风险列表：列表 + 筛选

- 操作：`GET /api/commits?page=1&size=3`（带 `X-API-Key`）
- 预期：`code=0`，`items` 3 条，按 `risk_score` 降序
- 实际：`code=0`，3 条，risk_score 0.3 / 0.2 / 0.1 降序 ✅

- 操作：`GET /api/commits?min_risk=0.2`
- 预期：只返回 `risk_score >= 0.2` 的提交（2 条）
- 实际：`total=2`，返回 0.3、0.2 两条 ✅

响应摘录（列表）：
```json
{"code":0,"message":"ok","data":{"total":3,"page":1,"size":3,
 "items":[{"commit_hash":"000...003","author_name":"seed-author-3","risk_score":0.3,"model_name":"seed_v1"}, ...]}}
```

### API-02 提交详情（确定哈希）

- 操作：`GET /api/commits/0000000000000000000000000000000000000001`
- 预期：`code=0`，含元信息 + 14 项 `features` + `explanation`
- 实际：`code=0`，`features` 14 项齐全（`ns/nd/nf/entropy/la/ld/lt/fix/ndev/age/nuc/exp/rexp/sexp`），`explanation` 为空数组（seed_v1 无 SHAP 归因）✅

响应摘录（详情）：
```json
{"code":0,"message":"ok","data":{"commit_hash":"000...001","risk_score":0.1,
 "features":{"ns":1.0986,"nd":1.6094,"nf":1.9459,"entropy":1.42,"la":-4.272,
 "ld":-5.2753,"lt":7.1136,"fix":1,"ndev":1.3863,"age":2.5257,"nuc":0.2513,
 "exp":5.7683,"rexp":3.8114,"sexp":2.8904},"explanation":[]}}
```

### API-03 趋势（周粒度）

- 操作：`GET /api/trends?granularity=week`
- 预期：`granularity=week`，`series` 按周聚合
- 实际：`granularity=week`，`series` 2 个周期（`2026-W31`、`2026-W32`），含 `commit_count`/`avg_risk`/`high_risk_count` ✅

响应摘录（趋势）：
```json
{"code":0,"message":"ok","data":{"granularity":"week","model_name":"seed_v1",
 "series":[{"period":"2026-W31","commit_count":2,"avg_risk":0.15,"high_risk_count":0},
           {"period":"2026-W32","commit_count":1,"avg_risk":0.3,"high_risk_count":0}]}}
```

### API-03 趋势（月粒度）

- 操作：`GET /api/trends?granularity=month`
- 预期：`granularity=month`，`series` 按月聚合
- 实际：`granularity=month`，`series` 1 个周期（`2026-08`，3 条提交，avg_risk 0.2）✅

响应摘录（月）：
```json
{"code":0,"message":"ok","data":{"granularity":"month","model_name":"seed_v1",
 "series":[{"period":"2026-08","commit_count":3,"avg_risk":0.2,"high_risk_count":0}]}}
```

### 鉴权失败

- 操作：`GET /api/commits`（不带 `X-API-Key`）
- 预期：HTTP 401 + `code=40100`
- 实际：HTTP 401，`{"code":40100,"message":"missing or invalid token","data":null}` ✅

## 三页人工冒烟（浏览器操作清单）

> 组件函数级回归（六项）已由审阅人复验通过；以下为真实浏览器操作的最小冒烟步骤，待浏览器执行后补实际页面截图。

| 页面 | 操作 | 预期页面结果 | 关键网络响应 |
|---|---|---|---|
| 风险列表 | 打开 `/`，点「查询」 | 表格显示 3 条 seed 提交，风险列 30%/20%/10% 降序 | `GET /api/commits` → code=0，3 条 |
| 风险列表（筛选） | `min_risk=0.2` 查询 | 只剩 2 条（30%、20%） | `GET /api/commits?min_risk=0.2` → total=2 |
| 提交详情 | 点第一条 → 跳 `/commit/000...003` | 显示风险值 30% + 14 项特征 | `GET /api/commits/000...003` → code=0 |
| 趋势看板 | 打开 `/trend`，粒度选「周」 | 折线 2 个点（W31/W32） | `GET /api/trends?granularity=week` → 2 周期 |
| 趋势看板 | 粒度选「月」 | 数据点 1 个（<2），不画折线，显明细表 + 「数据点不足」提示 | `GET /api/trends?granularity=month` → 1 周期 |

## 尚未覆盖（诚实标注）

- **浏览器实际执行**：上表为操作清单 + 预期，实际浏览器页面截图待执行后补。
- **等待中切换 / 乱序的浏览器复现**：组件函数级回归已复验通过，真实浏览器复现待补。
- **日期末秒端到端**：#62 已合入（10-16），可做端到端复核（待浏览器走查时验证）。
- **`POST /api/predict`**：已加详情页「重新预测」入口（PR #90），结果一次性展示，纳入页面联调范围。

## 落地结论

三查询接口（API-01/02/03）在真实后端 + SQLite 种子数据下，curl 层均返回 `code=0` 且字段齐全，鉴权失败按契约返回 401/40100；API-04 用真模型推理返回 risk_score + 非空 SHAP 归因。三页浏览器人工冒烟为操作清单 + 预期（待执行补截图）。前端送纯日期、错误码三态、粒度快照、requestId 防过期等行为与契约口径一致。#62 已合入，纯日期筛选的最后一天包含行为可做端到端复核。

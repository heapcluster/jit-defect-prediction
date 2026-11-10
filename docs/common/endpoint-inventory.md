# 集成测试端点清单（源码静态对照版）

> 状态：**这是清单与用例设计，不是测试通过报告。** 本清单由 `docs/api/*.md` 与 `backend/app/api/*.py` 静态对照得出；本轮**未取得运行时 `/openapi.json`**（本机无可用 Python 后端环境，原因见 [`neon-test-execution.md`](neon-test-execution.md)）。任何一行的 HTTP 实际结果仍为「未执行」。
>
> 采集：2026-11-10，分支 `test/neon-test-baseline`。接口覆盖率的分母以本文 11 个路由为准（与 `docs/api/README.md` 的「七份正文，共十一个路由」及 `backend/tests/test_mirror.py` 路径集一致）。

## 1 · 公共契约（全部端点共用）

| 项 | 事实 | 证据 |
|---|---|---|
| 鉴权 | Header `X-API-Key` 与 `config.API_TOKEN` 精确比较；缺失、错误、以及令牌未配置（fail closed）一律 HTTP 401 + `code=40100` | `backend/app/auth.py`、`backend/app/config.py` |
| 包络 | 成功 `{"code":0,"message":"ok","data":{…}}`；失败 `{"code":…,"message":…,"data":null}` | `backend/app/errors.py` |
| 业务码 | 仅 5 个：`0`→200、`40001`→400、`40100`→401、`40400`→404、`50000`→500 | `backend/app/errors.py` |
| 参数校验失败 | Pydantic 校验错误统一转 `40001`，message 形如 `参数非法：<参数名>` | `backend/app/errors.py` |
| 时间参数 | ISO 8601；纯日期作为 `end` 时扩到当天 `23:59:59.999999`（闭区间）；非法格式 → `40001` | `backend/app/timeutil.py` |
| 静态图 | `/static/**` 由中间件同样校验 `X-API-Key`，缺失 → 401 + `40100`（不为 `<img>` 开免鉴权） | `backend/app/main.py` |
| 内部错误 | 未捕获异常 → `50000`，message 固定 `internal error`，不回显堆栈 / SQL / 路径 | `backend/app/errors.py` |

## 2 · 端点清单

| # | 端点 | 鉴权 | 关键参数（必填 / 边界） | 成功 `data` 要点 | 可返回业务码 |
|---|---|---|---|---|---|
| 1 | `GET /api/commits` | `X-API-Key` | `page≥1`（默认 1）、`size` 1–100（默认 20）、`model_name?`、`start_time?`/`end_time?`（别名 `since`/`until`）、`q?` ≤64、`with_features?` ∈ {0,1}、`is_test?` ∈ {0,1} | `total`/`page`/`size`/`items[]`；`items[]` 含 `commit_hash`、`risk_score`、`model_name`、`features`（可为 null）、`is_bug_inducing`（null=未打标）；排序 `risk_score DESC, commit_hash ASC` | 40001、40100 |
| 2 | `GET /api/commits/{commit_hash}` | 同上 | 路径 `commit_hash` 必须 40 位十六进制（大写放行、内部转小写） | 单条默认模型结论 + `explanation[]` + `localization` + `fix_references`；缺特征/缺预测时 `risk_score`、`predicted_at` 为 null 而非报错 | 40001、40100、40400（仅 commit 行缺失） |
| 3 | `GET /api/models` | 同上 | `line?` ∈ {expert, semantic, fused, e2e}（空串同样 40001） | `lines[]{line,label,models[]}`，固定顺序 expert→semantic→fused→e2e；空线返回 `models=[]` 不报错 | 40001、40100 |
| 4 | `POST /api/predict` | 同上 | body `commit_hash`（必填，40 位十六进制）、`model_name?`（必须已加载） | `risk_score ∈ [0,1]`（5 位小数）、14 维 `features`、`explanation[]`、`predicted_at` | 40001、40100、40400（`SOURCE_REPO` 未配置 / 抽特征失败）、50000（模型注册表为空等） |
| 5 | `POST /api/sync` | 同上 | **query** 参数：`line?` ∈ 4 值、`model_name?`、`start_time?`/`end_time?`；不传时间则取最新一批（`SYNC_BATCH_LIMIT`） | `{"accepted": true}`，异步执行，进度走 `/api/sync/status` | 40001、40100、50000（已在同步中） |
| 6 | `GET /api/sync/status` | 同上 | 无 | `running`、`mode`、`scope`、`total`、`done`、`current_hash`、`started_at`、`last_error`；内存态，重启清零 | 40100 |
| 7 | `GET /api/trends` | 同上 | `granularity` ∈ {week, month}（默认 week）、`start_time?`/`end_time?`、`model_name?`（不校验是否已加载） | `series[]{period, commit_count, avg_risk, high_risk_count}`；周口径 `2024-W31`、月口径 `2024-07` | 40001、40100 |
| 8 | `GET /api/figures` | 同上 | `model_name` **必填**（缺失 → `参数非法：model_name`，空串 → `缺少 model_name`） | `line`、`metrics`（可为 null）、`figures[]`（固定序 roc/pr/confusion/calibration/effort/feat_importance，按存在项过滤） | 40001、40100、40400 |
| 9 | `GET /api/health` | 同上 | 无 | `status` ∈ {ok, degraded}、`db` ∈ {up, down}、`models_loaded`、`commit_count`、`prediction_count`、`last_sync_at`、`server_time`；DB 挂仍 HTTP 200 + `status=degraded` | 40100 |
| 10 | `GET /api/health/live` | 同上 | 无 | `status` 恒 `ok`（不碰 DB）、`server_time` | 40100 |
| 11 | `GET /api/health/ready` | 同上 | 无 | `status`、`db`、`models_loaded`、`server_time`；DB 不通或模型为 0 → `degraded`，HTTP 仍 200 | 40100 |

## 3 · 文档与代码不一致（6 处，均未提交 Issue，属待登记候选）

| # | 位置 | 文档口径 | 代码实际 | 对用例的影响 |
|---|---|---|---|---|
| D-01 | `docs/api/commits.md` | `features` 仅 `with_features=1` 时返回 | 未开启时键仍存在，值为 `null` | 断言「键不存在」会误判失败，应按「值为 null」写 |
| D-02 | `docs/api/commits.md` | 40400 = 提交**或特征**不存在 | 详情路由只在 commit 行缺失时 40400；缺特征走 `code=0` + null | 「缺特征」场景的预期码必须改 |
| D-03 | `docs/api/predict.md` | 多余字段 / 非法请求体返回 40001 | `PredictRequest` 未设 `extra="forbid"`，多余字段被静默忽略并 200 | 「非法请求体」用例需改用类型错误触发，不能靠多余字段 |
| D-04 | `docs/api/figures.md` | 40400 含「图文件不存在」 | 只查 DB，不校验 PNG 是否在盘；丢文件时本接口仍 200，坏在 `/static/**` | 不能把「丢图」写成 `/api/figures` 的 40400 |
| D-05 | `docs/api/sync.md` | 50000 = 同步中 / git 源不可达 / 内部错误 | git 不可达在后台线程抛 40400，只落 `last_error`，HTTP 拿不到 | 断言「HTTP 50000」会失败，应按 `sync/status.last_error` 断言 |
| D-06 | `docs/api/sync.md` | 未规定 `started_at` 序列化格式 | naive datetime 输出无 `Z`，与其余接口 `iso_z` 口径不一致 | 时间格式断言需按实际值放宽，或先修代码 |

补充（规格层，未计入上表）：`openspec/specs/nfr-evidence/spec.md` 要求提供 `backend/scripts/perf_loop.py` 与 `backend/scripts/security_cases.py`，但仓库**没有 `backend/scripts/` 目录**，`openspec/specs/` 下 `feedback`、`observability`、`ops`、`quality`、`ui` 五个能力目录为空目录（无 `spec.md`）。这两点会影响「非功能实测」与「验收逐 Scenario 对照」的取证路径。

## 4 · 四类场景用例设计（未执行）

**用例来源标注**：本节全部为 `[AI生成]`，由 DeepSeek-V4.1-Flash 依据本文 §2 与 `docs/api/*.md` 生成，Prompt 归档见 [`ai-prompts/neon-integration-cases.md`](ai-prompts/neon-integration-cases.md)。**人工复核：待 neon 逐条核对预期值与断言后，改为 `[AI生成-人工修改]` 或确认 `[AI生成]`。**

执行状态列统一为「未执行」，原因见 [`neon-test-execution.md`](neon-test-execution.md) §2；不得在未实跑前改成通过。

| # | 端点 | 正常 | 缺参 / 缺鉴权 | 非法参数 | 边界值 | 状态 |
|---|---|---|---|---|---|---|
| 1 | `GET /api/commits` | 带正确 key 请求默认分页，断言 `code=0`、`items[].risk_score ∈ [0,1]`、按风险降序 | 不带 `X-API-Key` → 401/40100 | `size=abc`、`with_features=2`、`q` 65 字、`start_time=2024-13-99` → 40001 | `size=1` 与 `size=100` 通过；`size=101` → 40001；`page=0` → 40001；`page` 超末页 → `items=[]` 且 `total` 不变 | 未执行 |
| 2 | `GET /api/commits/{hash}` | 取列表首条 hash 查详情，断言与列表同 `risk_score`、`explanation` 非空或为空数组 | 非法 key → 401/40100 | 39 位 / 41 位 / 含 `g` 的 hash → 40001 | 全大写 hash 与全小写返回同一条；不存在的 40 位 hash → 40400 | 未执行 |
| 3 | `GET /api/models` | 不带 `line`，断言 4 条 `lines`、顺序固定、`models[]` 非空（expert） | 非法 key → 401/40100 | `line=Expert`（大小写）、`line=""` → 40001 | `line=e2e` 时 `models=[]` 不报错 | 未执行 |
| 4 | `POST /api/predict` | 用已预测过的 hash + 已加载 `model_name`，断言 `0 ≤ risk_score ≤ 1`、`features` 14 项且列序与 `feature_order.txt` 一致 | 空 body / 缺 `commit_hash` → 40001 | `commit_hash` 非 40 位 → 40001；`model_name` 为未加载线（如 semantic）→ 40001 | 同 hash + 同模型重复预测 → 按 `prediction` 联合主键 `(commit_hash, model_name)` 幂等，仅一行且 `predicted_at` 刷新 | 未执行 |
| 5 | `POST /api/sync` | 不带时间触发最新一批，断言 `accepted=true`，随后 `sync/status.running` 可观测 | 非法 key → 401/40100 | `line=hierarchical`、`start_time=abc` → 40001 | 同步进行中再次触发 → 50000 且 message 为固定文案 | 未执行 |
| 6 | `GET /api/sync/status` | 触发同步后立即轮询，断言 `total ≥ done`、`mode` 合法 | 非法 key → 401/40100 | 无参数可传（多余 query 应被忽略，不报错） | 空闲时 `running=false`、`last_error=null`；重启后 `started_at=null` | 未执行 |
| 7 | `GET /api/trends` | `granularity=week`，断言 `series[].period` 匹配 `YYYY-Www`、`high_risk_count ≤ commit_count` | 非法 key → 401/40100 | `granularity=day`、`end_time=abc` → 40001 | 时间窗内无数据 → `series=[]` 且 `code=0`；`model_name` 传不存在模型 → 空 series（**不报 40400**） | 未执行 |
| 8 | `GET /api/figures` | `model_name=expert 线某模型`，断言 `figures[]` 顺序、`file_path` 指向 `/static/figures/...` | 不带 `model_name` → 40001；非法 key → 401/40100 | `model_name=""` → 40001 `缺少 model_name`；不存在模型 → 40400 | 该模型缺某些图时 `figures[]` 变短但 `code=0`；`/static/**` 不带 key → 401 | 未执行 |
| 9 | `GET /api/health` | 断言 `status=ok`、`models_loaded ≥ 1`、`server_time` 带 `Z` | 非法 key → 401/40100 | 无参数 | 停库后仍 HTTP 200 + `status=degraded`（不是 50000） | 未执行 |
| 10 | `GET /api/health/live` | 断言 `status=ok`，停库后仍 `ok` | 非法 key → 401/40100 | 无参数 | — | 未执行 |
| 11 | `GET /api/health/ready` | 断言 `status=ok`、`db=up`、`models_loaded ≥ 1` | 非法 key → 401/40100 | 无参数 | 停库或无模型 → `degraded`，HTTP 仍 200 | 未执行 |

补充要求（未执行）：跨模块链路一条「`POST /api/sync` 同步真实提交 → `commit_feature` 落 14 维 → `POST /api/predict` 推理 → `prediction` 落库 → `GET /api/commits` 查到 → 前端列表展示」；并发场景一条「两个客户端同时 `POST /api/sync`，断言一个成功、另一个 50000 且状态不被打乱」。

## 5 · 覆盖率口径

分母 11；已取得 HTTP 实际结果 0 个，**接口覆盖率以实测计为 0/11**（静态清单 11/11 只说明清单完整，不能替代请求成功）。四类场景共 11×4=44 条设计，执行 0 条。

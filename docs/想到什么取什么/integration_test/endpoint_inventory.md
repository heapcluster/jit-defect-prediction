# 集成测试端点清单（运行时对照版）

> 状态：清单 + 用例设计 + 实测结果索引。运行时 `/openapi.json` 共 11 个路径，与本文逐条一致；2026-11-15 在 `2734c1b` 上实跑 35 条用例，**34 通过 / 1 失败**。逐条结果与复现命令见 [`report.md`](report.md)。
>
> 采集：清单按运行时 `/openapi.json` 与代码逐端点核对（详情含 `model_name`、四线 25 模型登记在线、按线取特征与降级语义）。接口覆盖率的分母以本文 11 个路由为准（与 `docs/api/`「七份正文，共十一个路由」、`backend/tests/test_mirror.py` 路径集、运行时 `/openapi.json` 三者一致）。

## 0 · 重构期口径（2026-11-21 增补）

- **冻结**：§2 的 11 端点、§4 的 35 条用例与 34/1 结论、§5 覆盖率分母 11，均冻结于 `2734c1b`；重构后按运行时 `/openapi.json` 重算分母并另起执行记录。
- **端点增量（待新增，契约见 `docs/api/`）**：配置 `GET/PUT /api/config`、`PUT/DELETE /api/config/{key}`；数据集 `GET /api/datasets`、`/api/datasets/{id}`、`/api/datasets/{id}/commits`、`/api/datasets/{id}/export`；收集 `POST /api/collect`；清洗 `GET /api/clean/operations`、`POST /api/clean/preview`、`POST /api/clean/apply`；训练 `GET /api/algorithms`、`POST /api/train`、`GET /api/train/compare`；模型管理 `GET /api/models/status`、`POST /api/models/{name}/load|unload|reload`、`PUT /api/models/default`；评估 `POST /api/evaluate`、`GET /api/evaluate/metrics`；解释 `GET /api/explain/techniques`、`POST /api/explain`；源码 `GET /api/source/tree`、`GET /api/source/file`；任务 `GET /api/jobs`、`GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry|cancel`。
- **口径变更**：`POST /api/sync` 降为迁移期兼容入口（内部转 collect + predict_batch 两个 job）；`/api/sync/status` 目标读 job 表（现内存态为差距）；`/api/figures` 保留离线图集+默认阈值缓存，动态指标走 `/api/evaluate`；详情解释不再「仅 expert 有值」绝对化（兼容矩阵+空态原因）。
- **新增用例面（待设计待执行）**：新端点四类场景（正常/缺参/非法/边界）+ 任务五态流转 + 重启恢复 + 导出格式 + 评估 0.5 一致性 + 解释兼容矩阵 + 源码读取边界（过大/二进制/不存在）。

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
| 2 | `GET /api/commits/{commit_hash}` | 同上 | 路径 `commit_hash` 必须 40 位十六进制（大写放行、内部转小写）；`model_name?`（PR #216 新增：指定则查该模型 prediction，缺省查默认模型） | 单条结论 + `explanation[]` + `localization` + `fix_references`；缺特征/缺预测时 `risk_score`、`predicted_at` 为 null 而非报错 | 40001、40100、40400（仅 commit 行缺失） |
| 3 | `GET /api/models` | 同上 | `line?` ∈ {expert, semantic, fused, e2e}（空串同样 40001） | `lines[]{line,label,models[]}`，固定顺序 expert→semantic→fused→e2e；空线返回 `models=[]` 不报错 | 40001、40100 |
| 4 | `POST /api/predict` | 同上 | body `commit_hash`（必填，40 位十六进制）、`model_name?`（须在四线清单内且产物可用）；semantic/fused 需语义表、e2e 需文本表 + 编码器，缺任一 → 40001 明确文案（不 500） | `risk_score ∈ [0,1]`（5 位小数）、`features`（expert 14 维；semantic 768 / fused 782 展示口径见 `docs/README.md`）、`explanation[]`（仅 expert 线有值，其余为空数组）、`predicted_at` | 40001（含 `ModelUnavailable` 与 e2e 不可用）、40100、40400（`SOURCE_REPO` 未配置 / 抽特征失败）、50000（模型注册表为空等） |
| 5 | `POST /api/sync` | 同上 | **query** 参数：`line?` ∈ 4 值、`model_name?`、`start_time?`/`end_time?`；不传时间则取最新一批（`SYNC_BATCH_LIMIT`） | `{"accepted": true}`，异步执行，进度走 `/api/sync/status` | 40001、40100、50000（已在同步中） |
| 6 | `GET /api/sync/status` | 同上 | 无 | `running`、`mode`、`scope`、`total`、`done`、`current_hash`、`started_at`、`last_error`；内存态，重启清零 | 40100 |
| 7 | `GET /api/trends` | 同上 | `granularity` ∈ {week, month}（默认 week）、`start_time?`/`end_time?`、`model_name?`（不校验是否已加载） | `series[]{period, commit_count, avg_risk, high_risk_count}`；周口径 `2024-W31`、月口径 `2024-07` | 40001、40100 |
| 8 | `GET /api/figures` | 同上 | `model_name` **必填**（缺失 → `参数非法：model_name`，空串 → `缺少 model_name`） | `line`、`metrics`（可为 null）、`figures[]`（固定序 roc/pr/confusion/calibration/effort/feat_importance，按存在项过滤） | 40001、40100、40400 |
| 9 | `GET /api/health` | 同上 | 无 | `status` ∈ {ok, degraded}、`db` ∈ {up, down}、`models_loaded`、`commit_count`、`prediction_count`、`last_sync_at`、`server_time`；DB 挂仍 HTTP 200 + `status=degraded` | 40100 |
| 10 | `GET /api/health/live` | 同上 | 无 | `status` 恒 `ok`（不碰 DB）、`server_time` | 40100 |
| 11 | `GET /api/health/ready` | 同上 | 无 | `status`、`db`、`models_loaded`、`server_time`；DB 不通或模型为 0 → `degraded`，HTTP 仍 200 | 40100 |

### 2.1 模型覆盖口径（本轮实测，`2734c1b`）

`GET /api/models` 列出四线 25 个模型（expert 8 / semantic 8 / fused 8 / e2e 1），`model_registry` 只登记目录元数据、权重懒加载。但「列出」不等于「可预测」：

| 线 | 在线可用条件 | 干净检出下的实际状态 | 本轮实测 |
|---|---|---|---|
| expert（8） | `data_model/pipelines/expert/models/*.pkl` | 可用 | ✅ 8/8（`et_v1` 0.97637、`xgb_v1` 0.9993） |
| semantic（8）/ fused（8） | `pipelines/semantic/data/semantic_embeddings.npz`（后端默认路径与模型线 config 一致） | 本机产物已就位 | ✅ 各 7/8 通过（`xgb_semantic_v1` 0.55491、`xgb_fused_v1` 0.99433）；❌ 两个 tabnet 因 CUDA 权重无法加载（[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)） |
| e2e（1） | `pipelines/e2e/data/commit_text.csv` + `transformers` + `codebert_e2e_v1` 权重 | 产物已就位 | ✅ `0.44606`（首跑 62.3s，缓存后秒回）；容器内仍缺 `transformers`（[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219)） |

**25 模型逐条矩阵**由 `backend/scripts/online_models_matrix.py` 产出，本轮 **23 通过 / 2 失败**，逐条结论见 [`report.md`](report.md) §8。

`/api/models` 的 25 条记录不能当作 25 个可用模型；集成用例对「模型不可用」按「非 500 + 明确文案」断言（`T-IN-16`、安全用例 18 项）。

## 3 · 文档与实现偏差（复核后 6 条，已登记 Issue）

> 按 `2734c1b` 代码逐条复核：**D-01 不成立已剔除**；原 D-07（详情参数）并入下表；D-08/D-09 重新定性为「产物未按布局生成」而非「路径写错」；D-10 单独成 Issue（部署）。

| # | 位置 | 文档口径 / 期望 | 实际 | 对用例的影响 | 归属 |
|---|---|---|---|---|---|
| D-02 | `docs/api/commits.md` | 40400 = 提交**或特征**不存在 | 只在 commit 行缺失时 40400；缺特征/缺预测返回 `code=0` + `risk_score=null` | 「缺特征」场景的预期码必须改 | [#220](https://github.com/heapcluster/jit-defect-prediction/issues/220) |
| D-03 | `docs/api/predict.md` | 多余字段 / 非法请求体 → 40001 | `PredictRequest` 未设 `extra="forbid"`，多余字段被忽略并 200 | 非法请求体用例只能用类型错误触发 | #220（建议改代码） |
| D-04 | `docs/api/figures.md` | 40400 含「图文件不存在」 | 只查 DB，不校验 PNG 是否在盘；丢文件时接口 200，坏在 `/static/**` | 不能把「丢图」写成 `/api/figures` 的 40400 | #220 |
| D-05 | `docs/api/sync.md` | 50000 = 同步中 / git 源不可达 / 内部错误 | git 不可达在后台 worker 抛 40400，只落 `last_error`；HTTP 仅「已在同步中」返回 50000 | 断言 HTTP 50000 会失败，应按 `sync/status.last_error` 断言 | #220 |
| D-06 | `docs/api/sync.md` + `openspec/config.yaml` | 时间字段统一 UTC + `Z` | `sync/status.started_at` 实测形如 `2026-11-15T09:04:02.303942`，**无 `Z`**（其余接口带 `Z`） | 时间格式断言需放宽，或先修代码 | #220（建议改代码） |
| D-07 | `docs/api/commits.md` | 参数小节标题为「参数（列表）」 | 详情新增 query `model_name` 无对应参数条目（列表参数里早有 `model_name`） | 文档读者会以为详情不接受该参数 | #220 |

## 3.1 · 交付/部署缺口（非代码路径错误）

| 项 | 事实 | Issue |
|---|---|---|
| semantic/fused 产物 | `pipelines/semantic/config.py:21` 与后端默认值一致（`pipelines/semantic/data/*.npz`）；本机产物已就位，semantic / fused 各 7/8 通过（余 2 个是 tabnet） | [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)（本轮不复现，待确认关闭） |
| e2e 文本表 | `build_text_dataset.py` 生成 `pipelines/e2e/data/commit_text.csv`；本机已就位，e2e 实测 `0.44606` 通过 | #217 / #218 已关闭，剩余风险由 #226 跟踪 |
| tabnet 权重 | `tabnet_semantic_v1` / `tabnet_fused_v1` 保存于 CUDA，CPU 加载抛 `Attempting to deserialize object on a CUDA device`；**这是真缺陷** | [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) |
| 容器依赖 | `docker-compose` 用 `backend/Dockerfile` 构建，该文件未装 `transformers`（`environment.yml` 声明 4.46.1） | [#219](https://github.com/heapcluster/jit-defect-prediction/issues/219) |

补充（规格层，未计入上表）：`openspec/specs/` 下 `feedback`、`observability`、`ops`、`quality` 四个能力目录仍为空（无 `spec.md`），会影响「验收逐 Scenario 对照」的取证路径；`nfr-evidence` 要求的两个脚本已补（`backend/scripts/perf_loop.py`、`security_cases.py`）。

## 3.2 · 偏差复核更新（2026-11-21，main `3e72854`）

> 仅更新偏差状态，不改 §3 冻结表与本轮用例结论；重构后复跑须重新实测确认。

| # | 复核结论 | 证据（main 3e72854） |
|---|---|---|
| D-03 | **已修**：多余字段不再静默忽略 | `backend/app/api/predict.py:21` `ConfigDict(extra="forbid")` |
| D-04 | **已修**：缺图进 `missing[]`，不再把不可用路径当可用 | `backend/app/api/figures.py:84-87` 磁盘存在性校验 |
| D-06 | **已修**：`sync/status.started_at` 出参统一 UTC+Z | `backend/app/api/sync.py:366` `iso_z(...)` |
| D-02 | 待复核（缺特征/缺预测仍返回 null 的语义是否随新契约调整） | 见 `docs/api/commits.md` 修订 |
| D-05 | 待复核（git 不可达仍落 `last_error`；重构后错误语义走 job.error_log） | 见 `docs/api/sync.md` 修订 |
| D-07 | 文档修订中（详情 `model_name` 参数条目补齐） | W-B 修订 `docs/api/commits.md` |

## 4 · 四类场景用例（已执行，34/35 通过）

**用例来源标注**：本节全部为 `[AI生成]`，由 DeepSeek-V4.1-Flash 依据本文 §2 与 `docs/api/*.md` 生成，Prompt 归档见 [`prompts/integration_api_cases_01.md`](prompts/integration_api_cases_01.md)。核心业务断言（概率区间、14 维列序、鉴权码、排序、空结果语义）已逐条对照代码复核；**完整人工复核记录待补（不要求逐份签字）**。

下表是设计口径；逐条实测编号（T-IN-01~35）、实际输出与失败分析见 [`report.md`](report.md)。带参数的 9 个端点四类齐全；3 个健康探针无查询参数，「非法参数」不适用，以「缺令牌 + 无参数幂等」覆盖。

| # | 端点 | 正常 | 缺参 / 缺鉴权 | 非法参数 | 边界值 | 实测 |
|---|---|---|---|---|---|---|
| 1 | `GET /api/commits` | 带正确 key 请求默认分页，断言 `code=0`、`items[].risk_score ∈ [0,1]`、按风险降序 | 不带 `X-API-Key` → 401/40100 | `size=abc`、`with_features=2`、`q` 65 字、`start_time=2024-13-99` → 40001 | `size=1` 与 `size=100` 通过；`size=101` → 40001；`page=0` → 40001；`page` 超末页 → `items=[]` 且 `total` 不变 | PASS（T-IN-01~04） |
| 2 | `GET /api/commits/{hash}` | 取列表首条 hash 查详情，断言与列表同 `risk_score`、`explanation` 非空或为空数组；带 `model_name=<列表所选模型>` 时断言 `risk_score` 与该模型列表行一致（PR #216 修复点） | 非法 key → 401/40100 | 39 位 / 41 位 / 含 `g` 的 hash → 40001 | 全大写 hash 与全小写返回同一条；不存在的 40 位 hash → 40400；`model_name` 传不存在的模型 → 按代码应 200 + null（待实测确认，不要预设 40001/40400） | PASS（T-IN-05~08） |
| 3 | `GET /api/models` | 不带 `line`，断言 4 条 `lines`、顺序固定、`models[]` 非空（expert） | 非法 key → 401/40100 | `line=Expert`（大小写）、`line=""` → 40001 | `line=e2e` 时 `models=[]` 不报错 | PASS（T-IN-09~12） |
| 4 | `POST /api/predict` | 用已预测过的 hash + expert 线 `model_name`，断言 `0 ≤ risk_score ≤ 1`、`features` 14 项且列序与契约一致、`explanation` 非空 | 空 body / 缺 `commit_hash` → 40001 | `commit_hash` 非 40 位 → 40001；`model_name` 不在清单 → 40001；semantic/fused 在缺语义表时 → 40001 明确文案（非 500，见 D-08） | 同 hash + 同模型重复预测 → 按 `prediction` 联合主键 `(commit_hash, model_name)` 幂等，仅一行且 `predicted_at` 刷新；e2e 在缺文本表时 → 40001（见 D-09） | PASS（T-IN-13~16） |
| 5 | `POST /api/sync` | 不带时间触发最新一批，断言 `accepted=true`，随后 `sync/status.running` 可观测 | 非法 key → 401/40100 | `line=hierarchical`、`start_time=abc` → 40001 | 同步进行中再次触发 → 50000 且 message 为固定文案 | PASS（T-IN-19~21，含并发） |
| 6 | `GET /api/sync/status` | 触发同步后立即轮询，断言 `total ≥ done`、`mode` 合法 | 非法 key → 401/40100 | 无参数可传（多余 query 应被忽略，不报错） | 空闲时 `running=false`、`last_error=null`；重启后 `started_at=null` | PASS（T-IN-17/18） |

| 7 | `GET /api/trends` | `granularity=week`，断言 `series[].period` 匹配 `YYYY-Www`、`high_risk_count ≤ commit_count` | 非法 key → 401/40100 | `granularity=day`、`end_time=abc` → 40001 | 时间窗内无数据 → `series=[]` 且 `code=0`；`model_name` 传不存在模型 → 空 series（**不报 40400**） | PASS（T-IN-22~25） |
| 8 | `GET /api/figures` | `model_name=expert 线某模型`，断言 `figures[]` 顺序、`file_path` 指向 `/static/figures/...` | 不带 `model_name` → 40001；非法 key → 401/40100 | `model_name=""` → 40001 `缺少 model_name`；不存在模型 → 40400 | 该模型缺某些图时 `figures[]` 变短但 `code=0`；`/static/**` 不带 key → 401 | 26~28 PASS；**29 FAIL**（元数据 6 条齐全但 PNG 不在盘，带令牌 404 → BUG-02；补齐生成物后 200） |
| 9 | `GET /api/health` | 断言 `status=ok`、`models_loaded ≥ 1`、`server_time` 带 `Z` | 非法 key → 401/40100 | 无参数 | 停库后仍 HTTP 200 + `status=degraded`（不是 50000） | PASS（T-IN-30/31）；「停库降级」未构造 |
| 10 | `GET /api/health/live` | 断言 `status=ok`，停库后仍 `ok` | 非法 key → 401/40100 | 无参数 | — | PASS（T-IN-32） |
| 11 | `GET /api/health/ready` | 断言 `status=ok`、`db=up`、`models_loaded ≥ 1` | 非法 key → 401/40100 | 无参数 | 停库或无模型 → `degraded`，HTTP 仍 200 | PASS（T-IN-33/34）；「无模型」未构造 |

补充要求（已执行）：跨模块链路「`POST /api/sync` 同步真实提交 → `commit_feature` 落 14 维 → `POST /api/predict` 推理 → `prediction` 落库 → `GET /api/commits` 查到」已由 T-IN-35 与同步实测（25,404→25,414）覆盖；并发场景「两客户端同时 `POST /api/sync`」实测 200/500，状态不串扰（T-IN-21）。前端展示由浏览器走查覆盖（`../system_test/execution_records/`）。

## 5 · 覆盖率口径

分母 11；**11/11 端点均取得真实 HTTP 结果**（运行时 `/openapi.json` + 实际请求），接口覆盖率计 **100%**。用例 35 条全部执行，34 通过 / 1 失败（`report.md` §3）；设计表 44 条中，健康探针的「非法参数」9 条不适用（无查询参数），已并入「缺令牌 / 无参数幂等」用例。

后端单测基线：`254 passed`，行覆盖 **87.2%**（1333/1528）、分支 **76.2%**（256/336）。

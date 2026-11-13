# 集成测试端点清单（运行时对照版）

> 状态：清单 + 用例设计 + 实测结果索引。2026-11-10 初版为源码静态对照；**2026-11-12 已取得运行时 `/openapi.json`**（11 个路径，与本文逐条一致），并在本机真实环境执行 35 条用例（35/35 通过）。逐条结果与复现命令见 [`report.md`](report.md)。
>
> 采集：2026-11-10 初版；**2026-11-12 按合入的 PR #216（`afdee84`）更新**（详情新增 `model_name`、四线 25 模型登记在线、按线取特征与降级语义），同日完成运行时核对与实跑。分支 `test/neon-test-baseline`。接口覆盖率的分母以本文 11 个路由为准（与 `docs/api/README.md`「七份正文，共十一个路由」、`backend/tests/test_mirror.py` 路径集、运行时 `/openapi.json` 三者一致）。

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
| 4 | `POST /api/predict` | 同上 | body `commit_hash`（必填，40 位十六进制）、`model_name?`（须在四线清单内且产物可用）；semantic/fused 需语义表、e2e 需文本表 + 编码器，缺任一 → 40001 明确文案（不 500） | `risk_score ∈ [0,1]`（5 位小数）、`features`（expert 14 维；semantic 768 / fused 782 展示口径见 `docs/overview.md`）、`explanation[]`（仅 expert 线有值，其余为空数组）、`predicted_at` | 40001（含 `ModelUnavailable` 与 e2e 不可用）、40100、40400（`SOURCE_REPO` 未配置 / 抽特征失败）、50000（模型注册表为空等） |
| 5 | `POST /api/sync` | 同上 | **query** 参数：`line?` ∈ 4 值、`model_name?`、`start_time?`/`end_time?`；不传时间则取最新一批（`SYNC_BATCH_LIMIT`） | `{"accepted": true}`，异步执行，进度走 `/api/sync/status` | 40001、40100、50000（已在同步中） |
| 6 | `GET /api/sync/status` | 同上 | 无 | `running`、`mode`、`scope`、`total`、`done`、`current_hash`、`started_at`、`last_error`；内存态，重启清零 | 40100 |
| 7 | `GET /api/trends` | 同上 | `granularity` ∈ {week, month}（默认 week）、`start_time?`/`end_time?`、`model_name?`（不校验是否已加载） | `series[]{period, commit_count, avg_risk, high_risk_count}`；周口径 `2024-W31`、月口径 `2024-07` | 40001、40100 |
| 8 | `GET /api/figures` | 同上 | `model_name` **必填**（缺失 → `参数非法：model_name`，空串 → `缺少 model_name`） | `line`、`metrics`（可为 null）、`figures[]`（固定序 roc/pr/confusion/calibration/effort/feat_importance，按存在项过滤） | 40001、40100、40400 |
| 9 | `GET /api/health` | 同上 | 无 | `status` ∈ {ok, degraded}、`db` ∈ {up, down}、`models_loaded`、`commit_count`、`prediction_count`、`last_sync_at`、`server_time`；DB 挂仍 HTTP 200 + `status=degraded` | 40100 |
| 10 | `GET /api/health/live` | 同上 | 无 | `status` 恒 `ok`（不碰 DB）、`server_time` | 40100 |
| 11 | `GET /api/health/ready` | 同上 | 无 | `status`、`db`、`models_loaded`、`server_time`；DB 不通或模型为 0 → `degraded`，HTTP 仍 200 | 40100 |

### 2.1 模型覆盖口径（2026-11-12 更新，来自 PR #216 `afdee84`）

`GET /api/models` 现在列出四线 25 个模型（expert 8 / semantic 8 / fused 8 / e2e 1），`model_registry` 只登记目录元数据、权重懒加载。但「列出」不等于「可预测」：

| 线 | 在线可用条件 | 干净检出下的实际状态 | 2026-11-12 实测 |
|---|---|---|---|
| expert（8） | `data_model/pipelines/expert/models/*.pkl` | 可用 | ✅ 8/8 通过（`et_v1` 0.97637、`xgb_v1` 0.9993） |
| semantic（8）/ fused（8） | `pipelines/semantic/data/semantic_embeddings.npz`（后端默认路径与模型线 config 一致） | 产物原本未生成（仓库只有 `data_model/data/` 旧副本）；**补到约定路径后** 7/8 + 7/8 通过 | ✅ `xgb_semantic_v1` 0.55491、`xgb_fused_v1` 0.99433；❌ 两个 tabnet 因 CUDA 权重无法加载（[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)） |
| e2e（1） | `pipelines/e2e/data/commit_text.csv` + `transformers` + `codebert_e2e_v1` 权重 | 权重齐全（475MB），文本表原本未生成（脚本 `build_text_dataset.py` 存在）；补到约定路径后可用 | ✅ `0.44606`（与 PR #216 一致，首载 33.6s、复跑 0.3s）；容器内仍缺 `transformers`（[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219)） |

**25 模型逐条矩阵**见 `backend/scripts/evidence/2026-11-12-online-25.md`：23 通过 / 2 失败。

`/api/models` 的 25 条记录不能当作 25 个可用模型；集成用例对「模型不可用」按「非 500 + 明确文案」断言（`T-IN-16`、安全用例 12 项）。

## 3 · 文档与实现偏差（复核后 6 条，已登记 Issue）

> 2026-11-12 按 `afdee84` 代码逐条复核：**D-01 不成立已剔除**；原 D-07（详情参数）并入下表；D-08/D-09 重新定性为「产物未按布局生成」而非「路径写错」；D-10 单独成 Issue（部署）。

| # | 位置 | 文档口径 / 期望 | 实际 | 对用例的影响 | 归属 |
|---|---|---|---|---|---|
| D-02 | `docs/api/commits.md` | 40400 = 提交**或特征**不存在 | 只在 commit 行缺失时 40400；缺特征/缺预测返回 `code=0` + `risk_score=null` | 「缺特征」场景的预期码必须改 | [#220](https://github.com/heapcluster/jit-defect-prediction/issues/220) |
| D-03 | `docs/api/predict.md` | 多余字段 / 非法请求体 → 40001 | `PredictRequest` 未设 `extra="forbid"`，多余字段被忽略并 200 | 非法请求体用例只能用类型错误触发 | #220（建议改代码） |
| D-04 | `docs/api/figures.md` | 40400 含「图文件不存在」 | 只查 DB，不校验 PNG 是否在盘；丢文件时接口 200，坏在 `/static/**` | 不能把「丢图」写成 `/api/figures` 的 40400 | #220 |
| D-05 | `docs/api/sync.md` | 50000 = 同步中 / git 源不可达 / 内部错误 | git 不可达在后台 worker 抛 40400，只落 `last_error`；HTTP 仅「已在同步中」返回 50000 | 断言 HTTP 50000 会失败，应按 `sync/status.last_error` 断言 | #220 |
| D-06 | `docs/api/sync.md` + `openspec/config.yaml` | 时间字段统一 UTC + `Z` | `sync/status.started_at` 实测 `2026-11-12T09:04:02.303942`，**无 `Z`** | 时间格式断言需放宽，或先修代码 | #220（建议改代码） |
| D-07 | `docs/api/commits.md` | 参数小节标题为「参数（列表）」 | 详情新增 query `model_name` 无对应参数条目（列表参数里早有 `model_name`） | 文档读者会以为详情不接受该参数 | #220 |

## 3.1 · 交付/部署缺口（非代码路径错误）

| 项 | 事实 | Issue |
|---|---|---|
| semantic/fused 产物 | `pipelines/semantic/config.py:21` 与后端默认值一致（`pipelines/semantic/data/*.npz`），但该 npz 未生成；仓库只有 `data_model/data/` 旧副本。**补到约定路径后 7+7 个模型通过** | [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217) |
| e2e 文本表 | `build_text_dataset.py` 存在（`OUT_CSV=pipelines/e2e/data/commit_text.csv`），产物未生成；补齐后 e2e 实测 `0.44606` 通过 | #217（原 #218 已合并关闭） |
| tabnet 权重 | `tabnet_semantic_v1` / `tabnet_fused_v1` 保存于 CUDA，CPU 加载抛 `Attempting to deserialize object on a CUDA device`；**这是真缺陷** | [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) |
| 容器依赖 | `docker-compose` 用 `backend/Dockerfile` 构建，该文件未装 `transformers`（`environment.yml` 声明 4.46.1） | [#219](https://github.com/heapcluster/jit-defect-prediction/issues/219) |

补充（规格层，未计入上表）：`openspec/specs/` 下 `feedback`、`observability`、`ops`、`quality`、`ui` 五个能力目录为空目录（无 `spec.md`），会影响「验收逐 Scenario 对照」的取证路径；`nfr-evidence` 要求的两个脚本本轮已补（`backend/scripts/perf_loop.py`、`security_cases.py`）。

## 4 · 四类场景用例（已执行，35/35 通过）

**用例来源标注**：本节全部为 `[AI生成]`，由 DeepSeek-V4.1-Flash 依据本文 §2 与 `docs/api/*.md` 生成，Prompt 归档见 [`prompts/integration_api_cases_01.md`](prompts/integration_api_cases_01.md)。核心业务断言（概率区间、14 维列序、鉴权码、排序、空结果语义）已逐条对照代码复核；**人工签署待 neon 在验收环节确认**。

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
| 8 | `GET /api/figures` | `model_name=expert 线某模型`，断言 `figures[]` 顺序、`file_path` 指向 `/static/figures/...` | 不带 `model_name` → 40001；非法 key → 401/40100 | `model_name=""` → 40001 `缺少 model_name`；不存在模型 → 40400 | 该模型缺某些图时 `figures[]` 变短但 `code=0`；`/static/**` 不带 key → 401 | PASS（T-IN-26~29） |
| 9 | `GET /api/health` | 断言 `status=ok`、`models_loaded ≥ 1`、`server_time` 带 `Z` | 非法 key → 401/40100 | 无参数 | 停库后仍 HTTP 200 + `status=degraded`（不是 50000） | PASS（T-IN-30/31）；「停库降级」未构造 |
| 10 | `GET /api/health/live` | 断言 `status=ok`，停库后仍 `ok` | 非法 key → 401/40100 | 无参数 | — | PASS（T-IN-32） |
| 11 | `GET /api/health/ready` | 断言 `status=ok`、`db=up`、`models_loaded ≥ 1` | 非法 key → 401/40100 | 无参数 | 停库或无模型 → `degraded`，HTTP 仍 200 | PASS（T-IN-33/34）；「无模型」未构造 |

补充要求（已执行）：跨模块链路「`POST /api/sync` 同步真实提交 → `commit_feature` 落 14 维 → `POST /api/predict` 推理 → `prediction` 落库 → `GET /api/commits` 查到」已由 T-IN-35 与同步实测（25,285→25,307）覆盖；并发场景「两客户端同时 `POST /api/sync`」实测 200/500，状态不串扰（T-IN-21）。前端展示由浏览器走查覆盖（`../system_test/execution_records/`）。

## 5 · 覆盖率口径

分母 11；**11/11 端点均取得真实 HTTP 结果**（运行时 `/openapi.json` + 实际请求），接口覆盖率计 **100%**。用例 35 条全部执行且通过（`report.md` §3）；设计表 44 条中，健康探针的「非法参数」9 条不适用（无查询参数），已并入「缺令牌 / 无参数幂等」用例。

后端单测基线：`249 passed`，行覆盖 **85%**（分支覆盖 336 个分支、40 个部分覆盖）。

# 后端接口规格（API Spec）

> 来源：契约三（已并入本文件）**v1.7**（原 `docs/contracts/api-format.md`，已冻结 2026-09-19；v1.5 = 2026-10-11 补记时间区间语义，PR #62 / Issue #61；v1.6 = 2026-10-25 新增 §5 `POST /api/sync` 批量同步，路径数 4→5，来源 change `realtime-commit-sync`，裁定：蒋励；**v1.7 = 2026-10-25 新增 §6~§8 PR 实时预测三条端点（路径数 5→8），并把 §4 的在线模型清单口径回填为 #153 后的 8 模型**；此后版本号见文末变更日志逐条推进，**当前 = v2.3**）｜ 维护：吕建江
> **本文件是后端实现的唯一接口依据。冻结后改动走契约变更流程，不许口头改、不许前端/后端各写一份。**

## 一、通用约定

| 项 | 约定 |
|---|---|
| 前缀 | 一律 `/api` |
| 响应包络 | `{ "code": 0, "message": "ok", "data": {...} }` |
| 时间格式 | ISO 8601 带时区，如 `2026-09-16T08:30:00Z` |
| 概率字段 | `0.0`~`1.0` 小数，后端不返回 `"85%"` 字符串（前端转百分比） |
| 分页 | `page`（从 1）、`size`（默认 20，上限 100） |
| 鉴权 | 请求头 `X-API-Key`；缺失/不匹配 → 401。`四个接口一律适用，预测接口不例外` |
| 时间范围语义 | `start_time`/`end_time` 为**闭区间** `[start, end]`（按 `committed_at` 过滤）；**纯日期串**（`YYYY-MM-DD`）：start 解释为当天 `00:00:00.000000`、end 解释为当天 `23:59:59.999999`（**结束日含全天**）；带时间分量按原样；带时区先转 UTC；**紧凑基本格式（如 `20260803`、`20260803T090000`，含带 `Z`/偏移后缀变体）MUST 被拒（40001）**，同一日期只允许一种写法。前端 MUST NOT 依赖「手动补 `T23:59:59`」这类调用侧补丁 —— 区间语义由服务端统一解释，避免各调用方各写一套 |

### 鉴权细则

- 方案：固定令牌（API Key），**不做 JWT**（无多用户/权限分级/跨服务调用）。
- 令牌来源：服务端从 `.env` 读取，不入库、不写死代码；前端从构建期环境变量注入，不硬编码。
- 失败响应：`401` + `code=40100`，message 固定 `missing or invalid token`，不提示令牌哪一位错。
- 已接受的代价：无过期/轮换；令牌随前端产物下发浏览器，演示环境仅内网、数据不敏感，可接受。

## 二、错误码表

| code | HTTP | 含义 | message 示例 |
|---|---|---|---|
| 0 | 200 | 成功 | `ok` |
| 40001 | 400 | 参数非法 | `size 超过上限 100` |
| 40100 | 401 | 未通过鉴权 | `missing or invalid token` |
| 40400 | 404 | 目标不存在 | `commit not found` |
| 50000 | 500 | 服务内部错误 | `internal error`（**不得回显堆栈/SQL/路径**） |

## 三、接口清单

### 1. `GET /api/commits` —— 风险列表
请求：`page` `size` `min_risk` `model_name` `start_time` `end_time` `q`（搜索，≤64 字符；命中「哈希前缀 / 作者 / 提交信息」三者之一，纯查看过滤，不触发预测）
响应 `data`：`total` / `page` / `size` / `items[]`（每项 `commit_hash` `author_name` `committed_at` `message` `risk_score` `model_name`），按 `risk_score` 降序。

### 2. `GET /api/commits/{commit_hash}` —— 提交详情
响应 `data`：`commit_hash` `author_name` `committed_at` `message` `risk_score` `model_name` `features{14项}` `explanation[]{feature,contribution,direction}`。
- `features` 键名必须与 `feature-columns.md` 一致。
- **不返回真实标签**（predict 表无真实标签字段）。
- 提交存在但 `prediction` 无行：`code=0`，`risk_score`/`model_name` 为 `null`、`explanation` 为 `[]`（不是错误，前端渲染「尚未预测」），**不得返回 40400、不得用 0.0 冒充**。
- 若表内全局默认模型对该提交无预测，但该提交有其他在线模型预测，详情按该提交已有模型的版本序取最新一条，不得误报「尚未预测」。
- 提交存在但 `commit_feature` 无行：`code=0`，`features` 为 `null`（不得 40400、不得以 0 填充）。

### 3. `GET /api/trends` —— 缺陷引入趋势
请求：`granularity`(`week`/`month`) `start_time` `end_time` `model_name`
响应 `data`：`granularity` `model_name` `series[]`（每项 `period` `commit_count` `avg_risk` `high_risk_count`）。
- **「高风险」阈值 = 服务端常量 `0.5`（`risk_score>=0.5`），不开放请求参数**，后端算 `high_risk_count` 返回；前端不得重算。
- `series` 只返回单模型一组数据，不做同图多模型对比。

### 4. `POST /api/predict` —— 在线预测（课程硬要求：对外在线预测服务）
请求体：`{ "commit_hash": "40位十六进制", "model_name"?: "默认模型" }`（缺省取**冠军模型** `champion_model`，未配置时回退 `version_key` 最大者，口径同 §17）
响应 `data`：`commit_hash` `model_name` `risk_score` `predicted_at` `features{14项}` `explanation[]`（结构与第 2 节一致）。
- 本次演示的在线模型以 `MODEL_DIR/feature_order.txt` 的 `[models]` 段为准（当前 expert 全量 8 个：`lr_v1` / `rf_v1` / `xgb_v1` / `lgbm_v1` / `et_v1` / `svm_v1` / `mlp_deep_v1` / `tabnet_v1`，#153 组长裁定）；目录内其他训练权重不进入注册表。清单缺失或 `[feature_order]` 与契约二 14 项顺序不一致时，注册表保持空并记录服务端错误；查询接口仍可用，预测返回 50000。
- `features` 给**口径处理后的值**（除 `fix` 外取自然对数；`la/ld/lt/nuc` 先归一化）。
- 可配置 `SOURCE_REPO` 指向本地 Git 仓库副本（路径由服务端 `.env` 设置，不接受请求方传入）。提交或特征行缺失时，后端调用 `data_model/preparation/03_extract_features.py` 的单条 v1 入口，现算 14 项、落 `commit`/`commit_feature` 后实时推理；仓库 HEAD 必须包含目标非合并提交。未配置来源时保留原有只查库行为。
- 错误：缺哈希/非 40 位 → `40001`；未配置来源且哈希不在 `commit` 表，或已配置来源但目标不可达 → `40400`；仓库路径失效/抽取内部失败、模型加载失败 → `50000`（只写日志不回显路径）。
- **幂等**：同一 `(commit_hash, model_name)` 重复调用，库里只留最新一行，不得累积重复。
- 性能靶子：压测针对本接口，不拿查询接口代替。

### 5. `POST /api/sync` —— 批量同步最新提交并在线预测（change `realtime-commit-sync`）
请求：`limit`（默认 10，上限 50，越界 `40001`）。
响应 `data`：`tip`（本次同步到的最新提交哈希）/ `scanned` / `new` / `predicted[]`（每项 `commit_hash` `model_name` `risk_score`）/ `skipped[]`（每项 `commit_hash` `code` `message`）。
- 行为：对服务端 `SOURCE_REPO` 执行 `git fetch`（经命令行参数禁用代理）→ 确保最新提交 HEAD 可达 → 挑出**有效默认模型（§17）尚无 `prediction` 行**的哈希 → **逐条复用第 4 节单条链路**（现算特征、幂等写 `prediction`，一次写全部在线模型行）；本端点 MUST NOT 引入新的预测口径。判据 MUST NOT 只看「该提交是否被任意模型预测过」：那会让先被某个模型预测过的提交永久跳过，其余在线模型再也补不上。
- `SOURCE_REPO` 未配置 → `40400`；单条失败（如提交不可达）计入 `skipped` 不中断整批；无新提交时幂等返回 `new=0`；同一时刻仅允许一个同步任务，重入 → `50000`。
- 可选 `SYNC_ON_STARTUP=1`：服务启动后台预同步一次，失败只记日志不阻塞启动。
- **不做 PR 状态跟踪与删除**（预测对象是 commit；close/merged 的生命周期标记另行 change）。
- **耗时口径**：本端点不适用 500ms 靶子（§四 的性能靶子只针对 `POST /api/predict` 单条）。单条含全量历史扫描 + SHAP，实测约 3~8s/条（取决于 SOURCE_REPO 历史深度）；`limit=50` 最坏约数分钟且 HTTP 同步挂起 —— 演示与验收一律用 `SYNC_ON_STARTUP=1` 启动预同步或小 `limit`，不现场发大 limit。

### 6. `POST /api/sync-prs` —— 拉取 Camel open PR 并实时预测入库（change `realtime-pr-prediction`）
请求：`limit`（默认 10，上限 50，越界 `40001`）。
响应 `data`：`prs_scanned` / `commits_predicted` / `prs[]`（每项 `pr` `title` `commits_predicted`）/ `skipped[]`（每项 `pr` + `reason` 或 `commit` `code` `message`）。
- 行为：拉 GitHub 公开仓库的 open PR 清单 → 逐 PR `git fetch origin pull/<n>/head`（仅取对象，不 checkout，SOURCE_REPO 检出状态不变）→ 取该 PR 提交清单 → **逐提交复用 §4 的单条多模型链路**（一次现算特征、逐模型打分落 `prediction`）；本端点 MUST NOT 引入新的预测口径。
- `SOURCE_REPO` 未配置或失效 → `40400`；单 PR fetch 失败、单提交预测失败计入 `skipped` 不中断整批；PR 清单来自 GitHub REST API（`GITHUB_REPO`，未配 `GITHUB_TOKEN` 时受匿名限额约束）。
- **耗时口径同 §5**：不适用 500ms 靶子；单 PR 即多条提交 × 8 模型，`limit=30` 必然超过 10s，调用方必须放宽超时。

### 7. `GET /api/prs` —— open PR 聚合风险列表（change `realtime-pr-prediction`）
请求：`limit`（默认 20，上限 50）/ `model_name`（默认取**冠军模型**，口径同 §17；不在清单 → `40001`）。
响应 `data`：`items[]`（每项 `number` `title` `author` `state` `html_url` `updated_at` `risk_score` `commit_count` `predicted_count` `predicted_at`）/ `model_name` / `skipped`（聚合失败的 PR 数）。
- `risk_score` = 该 PR 各提交在指定模型下的**最高**风险分（无预测为 `null`，不得用 0.0 冒充）；`predicted_at` 为该 PR 最新一条预测的时间，ISO 8601 带 `Z`。
- **纯只读**：数据来自 GitHub API + `prediction` 表，**不依赖 `SOURCE_REPO`** —— 未配置历史索引时本端点照常返回库内已有数据，不得 40400。
- 单个 PR 的提交清单拉取失败只计入 `skipped`，其余 PR 照常返回，不整端 50000。

### 8. `GET /api/prs/{number}` —— 单个 PR 的提交级风险明细（change `realtime-pr-prediction`）
请求：`model_name`（口径同 §7）。
响应 `data`：`number` `title` `author` `state` `html_url` `updated_at` `model_name` / `commits[]`（每项 `sha` `message` `author` `risk_score` `predicted_at`，按 PR 内提交时间正序）。
- `commits[]` 与 GitHub 返回的提交清单一对应：库内无预测的提交 `risk_score`/`predicted_at` 为 `null`（「尚未预测」，不得 40400、不得用 0.0 冒充）；`message` 截断至 200 字符。
- 同 §7：纯只读，不依赖 `SOURCE_REPO`；PR 不存在按上游 404 映射 `50000`（不回显 GitHub 细节）。

### 9. `GET /api/commits/coverage` —— 已预测时间覆盖（change `startup-baseline-sync`）
请求：无参数。响应 `data`：`items[]`（每项 `model_name` `start` `end`，为该模型已预测 commit 的 `committed_at` 最小/最大值，ISO 8601 带 Z）。
- 纯只读，`MUST NOT` 触发预测；前端据此展示「已预测覆盖」并引导至「补齐到最新」。

### 10. `POST /api/sync/catchup` —— 补齐到最新（change `startup-baseline-sync`）
请求：`MUST NOT` 接受日期参数。响应 `data`：`mode` `new` `predicted[]` `skipped[]`。
- 补齐「git 有而 DB 无 prediction」的提交，受 `SYNC_CATCHUP_LIMIT` 安全上限约束，幂等。

### 11. `GET /api/sync/status` / `GET /api/sync/stream` —— 同步状态与进度（change `startup-baseline-sync`）
- `status` 返回 `running` `mode` `scope` `total` `done` `current_hash` `started_at` `last_error` 快照。
- `stream` 为 SSE（`text/event-stream`），状态变化时推送 `data: {...}`。

### 12. `PUT /api/commits/{commit_hash}/label` —— 人工反馈标签（change `feedback-observability`）
请求体：`{"is_defect": true | false | null}`。响应 `data`：`commit_hash` `is_defect` `labeled_at`。
- **三态语义**：`true` = 引入缺陷；`false` = 确认非缺陷（保留行，计入质量指标）；`null` = **撤销**（删除该提交的 `manual` 标签行，响应 `is_defect=null`、`labeled_at=null`）。撤销 `MUST NOT` 实现为 `false`，否则用户以为撤销、实际留下 tn/fp 样本。
- 以 `label_method="manual"` 写入/更新 `commit_label`，与 SZZ 自动标签靠唯一约束 `(commit_hash, label_method)` 隔离。
- `commit_hash` 不存在 → `40400`；请求体缺 `is_defect` 或值非布尔/非 `null` → `40001`；对未标注提交发 `null` 幂等返回 200（不报错、不建行）。
- `false` 与 `null` `MUST NOT` 混用：`false` 保留标签行（计入 `tn`/`fp`），`null` 删行（回到未标注，不计入任何指标）。

### 13. `GET /api/health` —— 健康检查与运行状态（change `feedback-observability`）
响应 `data`：`status`（`ok`/`degraded`）`db`（`up`/`down`）`models_loaded` `model_names` `commit_count` `prediction_count` `labeled_count` `last_sync_at` `server_time`。
- DB 不可达或模型数为 0 → `status="degraded"`，HTTP 仍为 200（`MUST NOT` 抛 50000）；响应 `MUST NOT` 回显连接串、口令、堆栈。

### 14. `GET /api/quality` —— 预测质量指标（change `quality-loop`）
请求：`model_name`（缺省取表内最新模型）、`threshold`（0.0~1.0，缺省取运行时 `high_risk_threshold`）、`start_time` / `end_time`（语义同 §1，按 `committed_at` 过滤）、`label_source`（`manual`｜`szz`，缺省 `manual`）。
响应 `data`：`model_name` `threshold` `label_source` `labeled_total` `evaluated` `tp` `fp` `tn` `fn` `precision` `recall` `f1` `accuracy` `false_discovery_rate` `avg_risk_defect` `avg_risk_clean` `recommended_threshold` `evaluated_at`。
- ground truth **只认** `label_method="manual"` 的人工标签，预测侧为 `risk_score >= threshold` 的二值判断。
- `label_source="szz"` 仅为对照视图（SZZ 自动标签自身有误报，`MUST NOT` 作为验收依据）；`label_source` 不在枚举内 → `40001`。
- `false_discovery_rate = fp / (tp + fp) = 1 - precision`，即「被判高风险但 label 说不是缺陷」的比例；分母为 0 → `null`。**注意它不等于 `fp/(fp+tn)` 的 FPR**（后者衡量「干净提交被误拦」），两者口径不同，字段名与文案不得混用。
- 无样本 → `code=0` 且 `evaluated=0`、派生指标为 `null`（`MUST NOT` 用 0.0 冒充）；`labeled_total` 含尚无 prediction 的标签，`evaluated` 只算真正参与比对的行。
- `threshold` 越界 → `40001`。

### 15. `GET /api/quality/dataset` —— 标签回流样本导出（change `quality-loop`）
响应 `data`：`count` `items[]`（`commit_hash` `is_defect` `labeled_at` `committed_at` `features`；无特征时 `features` 为 `null`）。
- 纯只读，供离线再训练消费；`MUST NOT` 触发预测或写入。

### 16. `POST /api/quality/calibrate` —— 阈值校准（change `quality-loop`）
请求体：`{"model_name": string|null}`（可省略）。响应 `data`：`model_name` `labeled_total` `evaluated` `applied` `reason` `before` `after`（`before`/`after` 均为 `threshold` `precision` `recall` `f1`）。
- 扫描 0.05~0.95（步长 0.05）选 F1 最高点（并列取更接近当前阈值者）；**仅在实质改善时**写入 `runtime_setting.high_risk_threshold` 并立即生效（无需重启），`mid_risk_threshold` 保持 `<= high`。
- 样本不足（`evaluated < 2`，或标签全为正/全为负）→ `code=0`、`applied=false`、`reason="insufficient_labels"`，`MUST NOT` 写入任何配置。
- 未改善 → `applied=false`、`reason="no_improvement"`。

> 阈值口径变更：§7/§8 的 `risk_level` 与趋势的 `high_risk_count` 自本版起读 `runtime_setting`（DB 优先、`.env` 兜底），不再直接取 `config.HIGH_RISK_THRESHOLD`；默认值不变。

### 17. `GET /api/config` / `PUT /api/config` —— 运行时配置（change `ops-hardening`）
`GET` 响应 `data`：`high_risk_threshold` `mid_risk_threshold` `champion_model` `sync_initial_limit` `sync_catchup_limit` `updated_at`。
`PUT` 请求体：`{"high_risk_threshold": float, "mid_risk_threshold": float, "champion_model": string|null}`，响应同 `GET`。
- 约束 `0.0 <= mid_risk_threshold <= high_risk_threshold <= 1.0`，越界 → `40001` 且不写入。
- 写入落 `runtime_setting` 并**立即生效**（`risk_level`、趋势高风险计数、PR 门禁同步跟随），无需重启。
- `champion_model` 是**全站默认模型的唯一定义点**：列表 / 详情 / 趋势 / 门禁 / **单条预测（§4）/ 同步判据（§5）** 都经同一处实现解析（`backend/app/services/champion.py`），MUST NOT 各写一份；必须是已加载的模型名，否则 `40001`；传空字符串表示清除，回退「`version_key` 最大者」（design D6）。
- **降级规则（明确写死，避免各端点各自解读）**：冠军已加载但 `prediction` 表里还没有它任何一行时，解析结果为「表内有行的模型里 `version_key` 最大者」，列表因此不会空；表里一行都没有（空库）时解析结果为空 → 读路径不加模型过滤，§4 未显式指定模型时回退注册表冠军。降级时响应 `MUST` 回显实际所用 `model_name`，前端据此标注（#183）。
- `sync_*_limit` 为只读（批处理规模仍归 `.env`）。

### 18. `GET /api/health/live` / `GET /api/health/ready` —— 探针拆分（change `ops-hardening`）
- `live`：`status` `server_time`，**不查 DB**（DB 故障不应触发进程重启）。
- `ready`：`status`（`ok`/`degraded`）`db`（`up`/`down`）`models_loaded` `server_time`；DB 不通或模型数为 0 → `degraded`，HTTP 仍为 200。
- 两者均需 `X-API-Key`（K8s probe 可用 `httpHeaders` 携带）。

### 19. `GET /api/prs/{number}/gate` —— CI 风险门禁（change `ops-hardening`）
请求：`model_name`（口径同 §7）。响应 `data`：`number` `model_name` `risk_score` `risk_level` `threshold` `blocked` `reason`。
- `blocked = risk_score >= threshold`（threshold 为运行时 `high_risk_threshold`）；无预测 → `risk_score=null`、`blocked=false`。
- 纯只读（只用 GitHub 提交清单 + 库内 prediction），可直接作为 CI required check。

### 20. `POST /api/webhook/github` —— GitHub 事件驱动（change `ops-hardening`）
请求头：`X-GitHub-Event`、`X-Hub-Signature-256`（HMAC-SHA256，密钥 `WEBHOOK_SECRET`）、`X-GitHub-Delivery`（投递 id，参与去重）。响应 `data`：`accepted` `duplicate` `event` `action` `triggered`。
- **鉴权机制为签名而非 `X-API-Key`**：GitHub 无法发送自定义令牌头；`WEBHOOK_SECRET` 未配置时一律 `40100`（fail closed）。
- `push` → 后台触发增量同步（`WEBHOOK_SYNC_LIMIT` 条）；`pull_request` 且 action ∈ {`opened`,`synchronize`,`reopened`} → 后台触发 PR 同步（`WEBHOOK_PR_LIMIT` 条，默认 1：每 PR 需一次 commit 清单调用，避免单个事件耗尽 GitHub 配额）。
- 立即返回（同步是分钟级操作，放后台线程）；并发由同步互斥锁兜底，重复事件只记日志。
- **投递去重**：GitHub 在超时/5xx 时会重投同一 `X-GitHub-Delivery`；验签通过后按进程内最近 256 个 id 判重，重复投递 → `duplicate=true`、`action=null`、`triggered=false`（`accepted` 仍为 `true`，避免 GitHub 继续重试）。缺 `X-GitHub-Delivery` 时不判重（兼容手工 `curl`）。
- 签名错误/缺失 → `40100`；非 JSON 对象体 → `40001`。

## 四、非功能要求与验证（必须有可出示证据）

| 要求 | 指标 | 验证 | 证据 |
|---|---|---|---|
| 性能 | `POST /api/predict` 95% 请求 < 500ms | 脚本循环 100 次统计分位数 | 脚本 + 输出截图，放 `backend/scripts/` |
| 安全 | 全部接口（含 `/api/sync`）均需鉴权；非法输入不泄露内部信息。**webhook 以 HMAC-SHA256 验签替代令牌鉴权**（GitHub 无法发送 `X-API-Key`），未配置密钥时 fail closed | ① 不带令牌→401；② 畸形参数→不含堆栈/SQL/路径；③ webhook 签名错误→40100 | 三组返回截图 |

## 五、不写进本规格

后端 Web 框架（FastAPI）、路由组织、前端请求库、部署地址端口、模型文件加载方式（跨线交付方案 A+C，见 `sprint0-scope.md` 第 4 节）。

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-10-28 | 2.3 | 后端线（吕建江） | **默认模型口径落到全部写入路径**：§5 同步判据改为「有效默认模型（§17）尚无 `prediction` 行」（原实现只看"任意模型有行即算已预测"，导致先被 `POST /api/predict` 打过的提交被永久跳过、其余在线模型补不上，与 change `realtime-commit-sync` 的全模型落库相反）；§17 补记**降级规则**与「列表/详情/趋势/门禁/§4/§5 共用同一处实现」（`backend/app/services/champion.py`），此前 §4 与读路径各解一次，冠军刚切换且尚无数据时同一提交会得到两份分、两个模型名 |
| 2026-10-27 | 2.2 | 后端线（吕建江） | **默认模型口径统一**：§4 单条预测、§7/§8 PR 查询、§19 门禁全部改读冠军模型（`champion_model`，未配置回退 `version_key` 最大者），修正此前「列表/详情/趋势走 champion、predict/门禁走 version_key」的双轨；**§1 登记 `q` 搜索参数**（哈希前缀/作者/提交信息，≤64 字符）；**§14 指标更名** `false_positive_rate` → `false_discovery_rate`（原实现是 `fp/(tp+fp)`＝1−precision，与 FPR 口径不同）；**§20 补 `WEBHOOK_PR_LIMIT`**。实现侧：catchup 差集改分批 SQL、webhook 去重改为「受理成功才登记」、git 仅对网络类错误重试 |
| 2026-10-27 | 2.1 | 后端线（吕建江） | **§14 质量视图补 `label_source` 入参与误拦指标**（`manual` 默认 / `szz` 仅对照，非法值 `40001`）；**§20 webhook 增加投递去重**：登记 `X-GitHub-Delivery` 请求头与 `duplicate` 响应字段，重复投递 `duplicate=true` 且不再派发后台同步 |
| 2026-10-27 | 2.0 | 后端线（吕建江） | **新增 §17~§20 运维加固四条（组）端点**（change `ops-hardening`）：§17 `GET/PUT /api/config` 阈值热更新、§18 `health/live`/`health/ready` 探针拆分、§19 `GET /api/prs/{number}/gate` CI 门禁、§20 `POST /api/webhook/github` 事件驱动（HMAC 验签）。§四安全行补记 webhook 的签名鉴权机制 |
| 2026-10-27 | 1.9 | 后端线（吕建江） | **新增 §14~§16 质量闭环三条端点**（change `quality-loop`）：`GET /api/quality`（人工标签 vs 预测的混淆矩阵与 P/R/F1）、`GET /api/quality/dataset`（回流样本导出）、`POST /api/quality/calibrate`（按标签校准阈值并落 `runtime_setting`）。**阈值来源变更**：§7/§8 `risk_level` 与趋势 `high_risk_count` 改读运行时配置，默认值不变。新增第 6 张表 `runtime_setting` |
| 2026-10-27 | 1.8 | 后端线（吕建江） | **§三「八个接口」→「接口清单」，补记 §9~§11 并新增 §12~§13**（change `feedback-observability`）：§9 coverage / §10 catchup / §11 sync status·stream（上一 change `startup-baseline-sync` 遗漏登记，一并补齐）；§12 人工反馈标签、§13 健康检查。§12 只用冻结错误码 40001/40400；§13 降级不抛 50000 且不回显连接细节 |
| 2026-10-25 | 1.6 | 蒋励（组长，代后端线起草，吕建江复核） | **§三「四个接口」→「五个接口」，新增 §5 `POST /api/sync` 批量同步**（change `realtime-commit-sync`）：fetch SOURCE_REPO → 挑新哈希 → 逐条复用 §4 单条链路；错误码用冻结集合；幂等 `new=0`；并发互斥；`SYNC_ON_STARTUP` 可选启动同步。**不做 PR 状态清理**（另行 change）、不承诺 500ms 靶子。§四安全行改为「全部接口」 |
| 2026-10-25 | 1.7 | 蒋励（组长，代后端线起草，吕建江复核） | **§三「五个接口」→「八个接口」，新增 §6~§8 PR 实时预测三条端点**（change `realtime-pr-prediction`）：`POST /api/sync-prs` 拉 open PR 逐提交复用 §4 多模型链路；`GET /api/prs` / `GET /api/prs/{number}` 只读查询（不依赖 SOURCE_REPO、逐 PR 失败隔离、`predicted_at` 带 Z）。**§4 在线模型清单口径回填为 #153 后的 8 模型**（原写 3 个，与 `feature_order.txt` 不一致）。§四安全行已覆盖「全部接口」，不再另改 |
| 2026-10-11 | 1.5 | 吕建江 | **补记时间区间语义（口径补充，0.1 步进）**：§一 新增「时间范围语义」行（闭区间 + 纯日期串 end 含结束日全天 + 紧凑基本格式拒收 40001 + 前端 MUST NOT 调用侧补丁及理由）。修复 Issue #61（结束日丢数据）。行为变化：end 纯日期串查询结果含结束日全天；紧凑格式由静默 00:00 改拒收。PR #62。1.5 以前的历史见 `docs/contracts/api-format.md` 的 git 历史（该目录已于 #55 重组移除） |

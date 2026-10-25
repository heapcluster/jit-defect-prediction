# 后端接口规格（API Spec）

> 来源：契约三（已并入本文件）**v1.5**（原 `docs/contracts/api-format.md`，已冻结 2026-09-19；v1.5 = 2026-10-11 补记时间区间语义，PR #62 / Issue #61）｜ 维护：吕建江
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

## 三、四个接口

### 1. `GET /api/commits` —— 风险列表
请求：`page` `size` `min_risk` `model_name` `start_time` `end_time`
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
请求体：`{ "commit_hash": "40位十六进制", "model_name"?: "默认最新" }`
响应 `data`：`commit_hash` `model_name` `risk_score` `predicted_at` `features{14项}` `explanation[]`（结构与第 2 节一致）。
- 本次演示的在线模型以 `MODEL_DIR/feature_order.txt` 的 `[models]` 段为准（当前 `lr_v1` / `rf_v1` / `xgb_v1`）；目录内其他训练权重不进入注册表。清单缺失或 `[feature_order]` 与契约二 14 项顺序不一致时，注册表保持空并记录服务端错误；查询接口仍可用，预测返回 50000。
- `features` 给**口径处理后的值**（除 `fix` 外取自然对数；`la/ld/lt/nuc` 先归一化）。
- 可配置 `SOURCE_REPO` 指向本地 Git 仓库副本（路径由服务端 `.env` 设置，不接受请求方传入）。提交或特征行缺失时，后端调用 `data_model/preparation/03_extract_features.py` 的单条 v1 入口，现算 14 项、落 `commit`/`commit_feature` 后实时推理；仓库 HEAD 必须包含目标非合并提交。未配置来源时保留原有只查库行为。
- 错误：缺哈希/非 40 位 → `40001`；未配置来源且哈希不在 `commit` 表，或已配置来源但目标不可达 → `40400`；仓库路径失效/抽取内部失败、模型加载失败 → `50000`（只写日志不回显路径）。
- **幂等**：同一 `(commit_hash, model_name)` 重复调用，库里只留最新一行，不得累积重复。
- 性能靶子：压测针对本接口，不拿查询接口代替。

## 四、非功能要求与验证（必须有可出示证据）

| 要求 | 指标 | 验证 | 证据 |
|---|---|---|---|
| 性能 | `POST /api/predict` 95% 请求 < 500ms | 脚本循环 100 次统计分位数 | 脚本 + 输出截图，放 `backend/scripts/` |
| 安全 | 四接口均需鉴权；非法输入不泄露内部信息 | ① 不带令牌→401；② 畸形参数→不含堆栈/SQL/路径 | 两组返回截图 |

## 五、不写进本规格

后端 Web 框架（FastAPI）、路由组织、前端请求库、部署地址端口、模型文件加载方式（跨线交付方案 A+C，见 `sprint0-scope.md` 第 4 节）。

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-10-11 | 1.5 | 吕建江 | **补记时间区间语义（口径补充，0.1 步进）**：§一 新增「时间范围语义」行（闭区间 + 纯日期串 end 含结束日全天 + 紧凑基本格式拒收 40001 + 前端 MUST NOT 调用侧补丁及理由）。修复 Issue #61（结束日丢数据）。行为变化：end 纯日期串查询结果含结束日全天；紧凑格式由静默 00:00 改拒收。PR #62。1.5 以前的历史见 `docs/contracts/api-format.md` 的 git 历史（该目录已于 #55 重组移除） |

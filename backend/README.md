# backend/ — 后端与接口线

> 版本 1.0 ｜ 更新 2026-09-17 ｜ 主笔 吕建江 ｜ 审核 苏哲勋

**负责人**：吕建江

## 职责

建数据库表、**加载模型并做在线推理**、预测接口、查询接口、结果解释模块、接口鉴权与输入校验。

## 交付物

接口实现、数据库表与 ER 图、模型加载与推理代码、鉴权与校验代码、OpenAPI（Swagger）接口文档。

## 目录结构（按这个放，不要新建同级目录）

| 路径 | 放什么 |
|---|---|
| `backend/app/` | 应用代码：入口、路由、模型层、校验、**模型加载器** |
| `backend/app/api/` | 四个接口的实现 |
| `backend/tests/` | 测试 |
| `backend/scripts/` | 性能与安全的验证脚本（契约第四节要求出证据，脚本放这里） |

## 技术栈与启动

```bash
# 依赖统一在 data_model/environment.yml（backend 不再有 requirements.txt）
conda env create -f data_model/environment.yml
conda activate jit-defect-prediction
uvicorn app.main:app --reload --port 8000
```

- 框架：FastAPI + SQLAlchemy + MySQL 8。
- 配置从 `.env` 读（本地创建，**不入库**）；`.env.example` **要入库**，列出所有键名、不含真实值。
- 加依赖时同步往 `data_model/environment.yml` 的 pip 段（backend 相关）加一行。

## 接口实现以 `docs/backend/api-spec.md` 为准

| 接口 | 用途 | 对应页面 |
|---|---|---|
| `GET /api/commits` | 风险列表：按 `risk_score` 降序，支持 `min_risk` / `model_name` / 时间范围筛选与分页 | 风险列表 |
| `GET /api/commits/{commit_hash}` | 提交详情：元信息 + 14 项特征值 + `explanation` | 提交详情 |
| `GET /api/trends` | 趋势聚合：`granularity=week/month` | 趋势看板 |
| **`POST /api/predict`** | **在线预测：传入 `commit_hash`，实时跑模型返回风险概率与解释** | 不绑页面（服务级入口，也是性能压测的靶子） |

- 响应包络统一 `{ "code": 0, "message": "ok", "data": {...} }`，前缀一律 `/api`。
- 错误码用契约表里那 5 个（`0` / `40001` / `40100` / `40400` / `50000`），**不要自造**。
- **`50000` 的 message 不得回显堆栈、SQL 语句、文件路径** —— 课程明确要求「非法输入不泄露内部信息」，内部细节只写服务端日志。**模型文件路径尤其不能回显**。
- 分页 `size` 默认 20、上限 100；鉴权失败返回 `40100`。**四个接口一律要鉴权，`POST /api/predict` 不例外**。
- `features` 的键名必须与 `docs/model/feature-columns.md` 完全一致。
- 前三个接口读库里**已落盘**的结果；第四个接口**实时推理**。**不要把 `POST /api/predict` 写成查库** —— 那样就失去了「在线预测服务」的意义，压测也证明不了模型推理的性能。

## 库表

按 `docs/design/data-fields.md` 建**四张表**：`commit` / `commit_label` / `commit_feature` / `prediction`。命名、类型、索引要求都以该契约为准（`commit_hash` 唯一索引、`committed_at` 普通索引）。

> **`commit_feature` 由后端建，跟前三张一起、同一份迁移脚本。** 它不在第一版 README 的三张表清单里，是这个清单当时写漏了 —— 字段从来没争议（`feature-columns.md` §1 早已定表名），争议只在「谁建」，现明确归后端。数据线只产出这份特征数据，不建库表（见 `data_model/README.md` 第 4 条铁规矩）。

**迁移方式自行决定**（Alembic 或建表 SQL 脚本都行），但要满足 —— 别人 clone 后一条命令能把库建好。这属于完成定义第 1 条「能在别人机器上跑起来」。

## 建表与入库

### 建表：SQL 或 Python 二选一

前提：目标 **MySQL 8 数据库已创建**，账号已有连接与建表权限。以下入口只建四张表，不创建数据库/用户、不授权、不灌数据；连接或权限错误需由管理员处理，不自动提权。

**还没有库？（一条命令建库 + 建两个库的表）** 先按 `backend/.env.example` 填好 `backend/.env` 的**五项连接字段**（`DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME`；口令单独一格、原样写不用转义），然后在仓库根跑：

```bash
python infra/setup_mysql.py          # 建 DB_NAME（默认 jit_demo）+ DB_TEST_NAME（默认 jit_test）并执行 infra/schema.sql
```

它按 `.env` 连库，账号有 `CREATE DATABASE` 权限即可（没有则不自动提权，用 `--root-password` 让脚本代建并授权），口令不会被打印。**四表 DDL 仍只有 `infra/schema.sql` 一份**，脚本不复制 DDL，所以下面两条入口的行为与幂等性不变。

只要 SQL 的等价路径（需要 root 或已授权账号）：`mysql -u root -p < backend/scripts/schema_mysql.sql`（= `CREATE DATABASE IF NOT EXISTS jit_demo`（utf8mb4 / utf8mb4_unicode_ci）+ `USE jit_demo` + `SOURCE infra/schema.sql`，跑完当场列出四张表）。

MySQL 安装、连接字段逐项说明、验收清单、常见报错见 **`docs/backend/mysql-setup.md`**（Issue #142）—— 那份是权威，本文不重复。

**mysql 客户端入口（cwd=仓库根，Git Bash / Bash）：**

```bash
# 替换为已有账号和数据库名；-p 交互输入密码，不把密码写进命令
MYSQL_USER=your_user
MYSQL_DATABASE=your_existing_database
mysql -u "$MYSQL_USER" -p "$MYSQL_DATABASE" < infra/schema.sql
```

即 `mysql -u<user> -p <database> < infra/schema.sql`；远端连接按实际环境补 `-h` / `-P`。`infra/schema.sql` 是 `Base.metadata` 经 SQLAlchemy MySQL dialect 编译的快照，保留全部列、主键、唯一约束和普通索引。四表均为 `CREATE TABLE IF NOT EXISTS`，索引内联，不另执行 `CREATE INDEX`；模型变更时须同步更新快照并通过 `tests/test_schema_sql.py` 的静态比对。

**Python 入口（cwd=backend）：**

```bash
# 按 backend/.env.example 配好 backend/.env 的五项连接字段（DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME）
python -m app.db init
```

`IF NOT EXISTS` 只跳过已有表，**不会校验或修复已有错误 schema，不是迁移工具**。SQL 路线建表后，将 `backend/.env` 的连接字段配成同一目标库，在 backend 运行现有只读索引自检：

```bash
python -c "from app.db import get_engine, _assert_indexes; _assert_indexes(get_engine())"
```

Python 建表入口已自动执行该自检；它只覆盖 `INDEX_ASSERTIONS` 的核心索引，不是完整列/键对照。若自检失败，应另走经授权的正式迁移，不因 SQL 执行成功便视为结构已修复。静态测试仅证明 SQL 与元数据一致，不能代替 MySQL 空库执行、重复执行及两条建表路径的实测。

### 灌入：统一走实时同步（2026-10-25 起不再有离线 CSV 灌库）

SQL **只建表**；业务数据由实时同步端点写入，同一份连接配置，无独立 SQL INSERT/upsert 路径。**离线灌库脚本 `app.ingest` 已彻底移除**（含其 CLI 入口与测试），历史 CSV 产物只作数据线归档，不再进入运行时。

```bash
# cwd=backend；两个端点都是长耗时（单条提交 × 8 模型约 4.1s），调用方须放宽超时
# 同步主干新提交：窗口内 Camel 最新提交逐条现算特征并预测入库
curl -X POST -H "X-API-Key: $API_TOKEN" "http://127.0.0.1:8000/api/sync?limit=50"
# 同步 open PR：逐 PR 取提交清单后逐条预测入库
curl -X POST -H "X-API-Key: $API_TOKEN" "http://127.0.0.1:8000/api/sync-prs?limit=10"
```

前置：在 `backend/.env` 配置 `SOURCE_REPO=<本地 Apache Camel Git 仓库绝对路径>`（历史索引），否则同步端点返回 40400。

入库幂等：按表幂等键 upsert（commit=commit_hash、label=(commit_hash, label_method)、feature=commit_hash、prediction=(commit_hash, model_name)，见 change `backend-db-and-query-api` design D4）。同一提交重复同步不增行；单条失败只计入 `skipped`，不中断整批。

## 模型从哪来（2026-09-16 已定：方案 A + C）

**A（后端加载模型文件）**：后端启动时从 `data_model/pipelines/expert/models/` 加载 `.pkl` 文件，供 `POST /api/predict` 实时推理。

新提交现算特征需在 `backend/.env` 设置 `SOURCE_REPO=<本地 Apache Camel Git 仓库绝对路径>`，并确保目标提交已被该仓库 HEAD 包含；未设置时接口只使用已灌库的特征。首次现算要扫描 Git 历史，不能把功能测试通过当作 500ms 性能验收，须在真实 Camel 副本上另测。

- 模型文件路径与特征顺序由契约约定，见 `docs/design/sprint0-scope.md` 第 4 节「跨线接口已定」。
- **特征顺序以 `docs/model/feature-columns.md` 为准**，不要按 `dict` 的插入顺序自己猜 —— 顺序错了模型不报错，只会给出错误答案。

**C（离线预测结果入库）**：数据线批量跑完，把结果写进 `prediction` 表；前三个查询接口读它。

**为什么两个都要**：历史全量提交不可能每翻一页都实时推理 —— 风险列表与趋势看板必须读预置结果（C）。而课程要求「在线预测服务」，新提交进来要能立刻出概率，这只能靠实时推理（A）。**两者写同一张 `prediction` 表，靠 `model_name` 区分。**

**不选 B（后端调推理脚本）**：每次预测起一个 Python 进程，光解释器启动就几百毫秒，过不了契约第四节「95% < 500ms」。

## 两条非功能要求（课程评分点，必须留证据）

| 要求 | 指标 | 证据形式 |
|---|---|---|
| 性能 | **`POST /api/predict`** 95% 的请求 < 500ms | 循环发 100 次请求的脚本 + 响应时间分位数输出 |
| 安全 | 四个接口均需鉴权；非法输入不泄露内部信息 | ① 不带令牌请求 → 401；② 发送畸形参数 → 返回中不含堆栈 / SQL / 路径 |

**只写「已实现」不算证据。** 脚本放 `backend/scripts/`，结果截图或输出放 `docs/` 或 `backend/`。

> 性能压测请针对 `POST /api/predict`，别拿查询接口代替 —— 查询接口走索引，快是自然的，证明不了模型推理的性能。

## 边界

- **不改特征定义**（要改走契约变更）、**不写页面**。
- **不改打标与特征计算逻辑** —— 那是数据与模型线的目录。
- 模型从哪来：**已裁定 A+C**（依据飞书《讨论0915-项目启动与分工》，规格见 `openspec/changes/model-training-and-delivery/`）。
  - 方案 A：数据线交付 `.pkl` 与特征顺序清单，本线启动时加载；
  - 方案 C：数据线产出 `prediction_result.csv`（字段对应契约一表三）作离线评估对照；**入库只走本线的实时同步端点**（`POST /api/sync` / `POST /api/sync-prs`，离线 CSV 灌库已于 2026-10-25 移除）—— 数据线只产出结果文件、不碰数据库。
- 只在本目录内写代码。

---

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-09-17 | 1.0 | 吕建江 | 补齐版本头与变更日志（**正文本轮一字未改**）：线的职责、目录结构、启动命令、边界、两项非功能要求的证据要求。正文「模型从哪来」的回填由 PR #21（`898d965c`）完成，不计入本文件的变更 |


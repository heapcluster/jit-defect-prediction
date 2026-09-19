# backend/ — 后端与接口线

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
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --port 8000
```

- 框架：FastAPI + SQLAlchemy + MySQL 8。
- 配置从 `.env` 读（本地创建，**不入库**）；`.env.example` **要入库**，列出所有键名、不含真实值。
- 加依赖时同步往 `backend/requirements.txt` 加一行。

## 接口实现以 `docs/contracts/api-format.md` 为准

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
- `features` 的键名必须与 `docs/contracts/feature-columns.md` 完全一致。
- 前三个接口读库里**已落盘**的结果；第四个接口**实时推理**。**不要把 `POST /api/predict` 写成查库** —— 那样就失去了「在线预测服务」的意义，压测也证明不了模型推理的性能。

## 库表

按 `docs/contracts/data-fields.md` 建**四张表**：`commit` / `commit_label` / `commit_feature` / `prediction`。命名、类型、索引要求都以该契约为准（`commit_hash` 唯一索引、`committed_at` 普通索引）。

> **`commit_feature` 由后端建，跟前三张一起、同一份迁移脚本。** 它不在第一版 README 的三张表清单里，是这个清单当时写漏了 —— 字段从来没争议（`feature-columns.md` §1 早已定表名），争议只在「谁建」，现明确归后端。数据线只产出这份特征数据，不建库表（见 `data_model/README.md` 第 4 条铁规矩）。

**迁移方式自行决定**（Alembic 或建表 SQL 脚本都行），但要满足 —— 别人 clone 后一条命令能把库建好。这属于完成定义第 1 条「能在别人机器上跑起来」。

## 建库与灌入（一条命令）

```bash
# 建四张表（先按 .env.example 配好 .env 的 DATABASE_URL）
python -m app.db init

# 灌入数据线产物（前提：先跑 data_model 01–04；prediction_result.csv 来自方案 C 离线预测，不来自 01–04）
python -m app.ingest commits     <提交清单.csv>
python -m app.ingest labels      <标签表.csv>
python -m app.ingest features    <特征表.csv>
python -m app.ingest predictions <prediction_result.csv>
```

灌入幂等：同一文件重跑不增行；按表幂等键 upsert（commit=commit_hash、label=(commit_hash, label_method)、feature=commit_hash、prediction=(commit_hash, model_name)，见 change `backend-db-and-query-api` design D4）。缺主键字段的行整批回滚并报行号。

## 模型从哪来（2026-09-16 已定：方案 A + C）

**A（后端加载模型文件）**：后端启动时从 `data_model/models/` 加载 `.pkl` 文件，供 `POST /api/predict` 实时推理。

- 模型文件路径与特征顺序由契约约定，见 `docs/sprint0-scope.md` 第 4 节「跨线接口已定」。
- **特征顺序以 `docs/contracts/feature-columns.md` 为准**，不要按 `dict` 的插入顺序自己猜 —— 顺序错了模型不报错，只会给出错误答案。

**C（离线预测结果入库）**：数据线批量跑完，把结果写进 `prediction` 表；前三个查询接口读它。

**为什么两个都要**：11,050 条提交不可能每翻一页都实时推理 —— 风险列表与趋势看板必须读预置结果（C）。而课程要求「在线预测服务」，新提交进来要能立刻出概率，这只能靠实时推理（A）。**两者写同一张 `prediction` 表，靠 `model_name` 区分。**

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
  - 方案 C：数据线产出 `prediction_result.csv`（字段对应契约一表三），**由本线灌入 `prediction` 表** —— 数据线只产出结果文件、不碰数据库。
- 只在本目录内写代码。

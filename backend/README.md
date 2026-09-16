# backend/ — 后端与接口线

**负责人**：吕建江

## 职责

建数据库表、预测接口、查询接口、结果解释模块、接口鉴权与输入校验。

## 交付物

接口实现、数据库表与 ER 图、鉴权与校验代码、OpenAPI（Swagger）接口文档。

## 目录结构（按这个放，不要新建同级目录）

| 路径 | 放什么 |
|---|---|
| `backend/app/` | 应用代码：入口、路由、模型层、校验 |
| `backend/app/api/` | 三个接口的实现 |
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

- 响应包络统一 `{ "code": 0, "message": "ok", "data": {...} }`，前缀一律 `/api`。
- 错误码用契约表里那 5 个（`0` / `40001` / `40100` / `40400` / `50000`），**不要自造**。
- **`50000` 的 message 不得回显堆栈、SQL 语句、文件路径** —— 课程明确要求「非法输入不泄露内部信息」，内部细节只写服务端日志。
- 分页 `size` 默认 20、上限 100；鉴权失败返回 `40100`。
- `features` 的键名必须与 `docs/contracts/feature-columns.md` 完全一致。

## 库表

按 `docs/contracts/data-fields.md` 建三张表：`commit` / `commit_label` / `prediction`。命名、类型、索引要求都以该契约为准（`commit_hash` 唯一索引、`committed_at` 普通索引）。

**迁移方式自行决定**（Alembic 或建表 SQL 脚本都行），但要满足 —— 别人 clone 后一条命令能把库建好。这属于完成定义第 1 条「能在别人机器上跑起来」。

## 两条非功能要求（课程评分点，必须留证据）

| 要求 | 指标 | 证据形式 |
|---|---|---|
| 性能 | 预测接口 95% 的请求 < 500ms | 循环发 100 次请求的脚本 + 响应时间分位数输出 |
| 安全 | 需鉴权；非法输入不泄露内部信息 | ① 不带令牌请求 → 401；② 发送畸形参数 → 返回中不含堆栈 / SQL / 路径 |

**只写「已实现」不算证据。** 脚本放 `backend/scripts/`，结果截图或输出放 `docs/` 或 `backend/`。

## 边界

- **不改特征定义**（要改走契约变更）、**不写页面**。
- 模型从哪来：见 `data_model/README.md` 末节，**待启动会定**。
- 只在本目录内写代码。

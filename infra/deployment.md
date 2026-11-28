# infra · 工程化支撑

本目录存放**与业务逻辑无关、但建库 / 初始化 / 交付需要**的工程化文件。业务代码不放这里。

系统按**本机部署**交付：MySQL 运行在本机，后端由 Uvicorn 启动，前端由 Vite 开发服务或静态产物托管；不提供 Dockerfile 与容器编排。

## 1 目录内容

| 文件 | 作用 |
|---|---|
| `schema.sql` | 15 张表的建表 DDL，**建表唯一真源**；不预置任何用户 |
| `setup_mysql.py` | 创建 `jit_demo` / `jit_test` 两个库并执行 `schema.sql` |
| `tests/` | 本目录自身的自测，不含业务与数据库测试 |

## 2 职责边界

- **只管**：建表脚本、初始化脚本与交付说明。
- **不管**：业务逻辑与接口契约（见 `docs/`）、各端测试用例（见 `backend/tests/`、`frontend/tests/`、`infra/tests/`）。
- 不提供镜像定义与编排文件；运行步骤见第 3 节。

## 3 本机启动

1. **准备 MySQL**：本机 MySQL 8.0 可用，准备好具备建库权限的账号。
2. **初始化数据库**：在仓库根运行 `python infra/setup_mysql.py`，创建 `jit_demo` / `jit_test` 并执行 `schema.sql`；也可在 `backend/` 运行 `python -m app.cli init-db` 只建业务库。
3. **配置后端**：复制 `backend/.env.example` 为 `backend/.env`，填入 MySQL 连接。
4. **创建账号**：在 `backend/` 运行 `python -m app.cli create-user`，口令由命令行交互输入。
5. **启动后端**：在 `backend/` 运行 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
6. **启动前端**：在 `frontend/` 运行 `npm ci`、`npm run dev -- --host 127.0.0.1`，打开 http://127.0.0.1:5173/ 。
7. **健康检查**：

```bash
curl http://127.0.0.1:8000/api/health
# 期望 {"code":0,"message":"ok","data":{"status":"ok"}}
```

- 健康检查与登录接口无需会话；其余 `/api/**` 需要登录后的 `jit_session` Cookie。
- `infra/schema.sql` 建立 15 张表，不创建任何用户；演示账号由操作者自行创建。
- 旧 7 表或 12 表数据库不会被自动迁移；请在隔离库重建后重新导入数据。

## 4 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | — | MySQL 连接 |
| `DB_TEST_NAME` | `jit_test` | pytest 专用测试库 |
| `GITHUB_TOKEN` | 空 | GitHub 接口凭证，可选，仅提高限额；页面不要求填写 |
| `GITEE_TOKEN` | 空 | Gitee 接口凭证，可选，仅提高限额；页面不要求填写 |
| `MODEL_DIR` | `temp/models` | 模型文件根目录 |
| `SEMANTIC_EMBEDDINGS` | 空 | 可选的离线语义向量缓存目录 |
| `SEMANTIC_TEXT_MODEL` | 空 | 本地 CodeBERT-base 权重目录或标识 |
| `SEMANTIC_MAX_LEN` | `512` | 语义编码截断长度 |

- 不提供 `API_TOKEN` / `X-API-Key`，鉴权统一走登录会话。
- 不提供 `SOURCE_REPO` / `SYNC_*`，仓库由收集任务参数显式指定。
- 只访问公开仓库；触发平台接口限流时提示稍后重试。

## 5 产物与数据

- 上传、任务产物、数据集、模型与评估图的目录规则见 [`../docs/约束/artifacts.md`](../docs/约束/artifacts.md)。
- 模型文件由算法决定：sklearn 为 `.pkl`，dnn / tabnet 为 `.pt`；不随代码交付分发。
- 登录会话存 MySQL `user_session`，登出删除会话行。

## 6 交付边界

- 不含：模型权重（`.pkl` / `.pt`）、数据集、`temp/`、`.env`、任何密钥。
- 数据库初始状态由 `infra/schema.sql` 决定；演示账号由操作者自行创建。
- 不改：业务逻辑与接口契约（以 `docs/` 为准）。

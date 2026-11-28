# 技术栈与配置

## 1 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11+、FastAPI、SQLAlchemy、Uvicorn |
| 模型与数据处理 | scikit-learn、XGBoost、LightGBM、PyTorch、pytorch-tabnet、transformers（CodeBERT-base）、pandas、imbalanced-learn、openpyxl、matplotlib |
| 数据库 | MySQL 8.0 |
| 前端 | Vue 3、Vite、Element Plus、ECharts、vue-router、axios |
| 测试 | pytest（后端）、vitest（前端） |
| 部署 | 本机部署：conda 环境运行 Uvicorn，前端由 Vite 开发服务或静态产物托管；不使用容器 |

- 语义线：本地 CodeBERT-base 编码 commit message 与 diff，mean pooling 取句向量，`max_len=512`；不调用外部推理服务。
- 会话：登录会话写入 MySQL `user_session`，Cookie 只存原始令牌，库内存 SHA-256。
- 模型产物：sklearn 算法用 joblib 存 `.pkl`；dnn / tabnet 用 `torch.save` 存单文件 `.pt`，内含结构与预处理。

## 2 配置项

配置只通过环境变量注入，不写入仓库、不下发前端。

| 变量 | 用途 |
|---|---|
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | 数据库连接 |
| `GITHUB_TOKEN` | GitHub 接口凭证，可选，仅提高限额；页面不要求填写 |
| `GITEE_TOKEN` | Gitee 接口凭证，可选，仅提高限额；页面不要求填写 |
| `MODEL_DIR` | 模型文件根目录，默认 `temp/models` |
| `SEMANTIC_EMBEDDINGS` | 可选的离线语义向量缓存目录；缺省时按本地模型实时编码 |
| `SEMANTIC_TEXT_MODEL` | 本地 CodeBERT-base 权重目录或标识 |
| `SEMANTIC_MAX_LEN` | 语义编码截断长度，固定 512 |

- 平台 token 不进入任何页面、不按用户存储。
- 用户级配置只存 `user_config`，系统级参数只走环境变量。

## 3 运行

| 场景 | 命令 |
|---|---|
| 本地后端 | `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| 本地前端 | `cd frontend && npm run dev -- --host 127.0.0.1` |
| 建库 | `cd backend && python -m app.cli init-db` |
| 创建账号 | `cd backend && python -m app.cli create-user`，密码交互输入 |

- 后端与前端均在本机 `127.0.0.1` 运行；数据库使用本机 MySQL 8.0，连接信息只通过环境变量注入。

## 4 约束

- 不在代码中硬编码密钥、地址与用户标识。
- 新增依赖须能通过现有后端 pytest、前端构建与 `infra/tests` 流程。
- 前端不得直连数据库或模型进程，只能调用 `/api`。
- 平台接口只访问公开仓库；不要求页面填写 Token，触发平台限流时提示稍后重试。

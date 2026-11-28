# 即时软件缺陷预测（JIT Defect Prediction）Web 系统

基于提交级特征（Kamei 14 项）或 CodeBERT 语义向量，预测代码变更引入缺陷的风险。登录后顶级页面为数据存储、数据收集、数据清洗、模型训练、模型预测、模型评估；预测详情、解释与缺陷定位归入预测页，个人配置归入数据存储页。

本文件是**仓库入口**：怎么起、怎么跑、测试怎么执行。设计口径以 [docs/index.md](docs/index.md) 为唯一入口。

## 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL 8.0
- 前端：Vue 3 + Vite + Element Plus + ECharts
- 模型与数据：scikit-learn / XGBoost / LightGBM / PyTorch / pytorch-tabnet / CodeBERT-base / pandas

## 目录

| 目录 | 说明 |
|---|---|
| `backend/` | FastAPI 应用与 pytest 用例 |
| `frontend/` | Vue 3 单页应用与 vitest 用例 |
| `data_model/` | 特征计算、SZZ 打标、训练与离线评估 |
| `infra/` | 建表 DDL、工程化脚本与交付说明，见 [infra/deployment.md](infra/deployment.md) |
| `docs/` | 设计真源：功能点、界面、接口、数据库、约束，入口见 [docs/index.md](docs/index.md) |
| `openspec/` | **历史规格归档**，不作为实现或验收依据 |
| `temp/` | 运行时产物根目录（上传、任务产物、数据集、模型、评估图），不提交 |

### 代码分层

- `backend/app/api/`：HTTP 路由与请求校验，薄层。
- `backend/app/services/`：任务执行与领域逻辑；解释、定位、diff、校验都放这里。
- `backend/app/models.py` / `db.py`：ORM 与建库，必须与 `infra/schema.sql` 一致。
- `backend/app/auth.py`：会话鉴权；`schemas.py`：请求 / 响应模型；`config.py`：环境变量。
- `frontend/src/views/`：页面组件；`api/`：接口封装；`router/`：路由。
- 模块之间只通过产物文件与 manifest 交接，不共享内存状态。

## 一、本机开发

1. **准备环境**：`conda env create -f data_model/environment.yml`，再 `conda activate jit-defect-prediction`；前端按 `frontend/package.json` 的 Node 版本。
2. **配置后端**：`cp backend/.env.example backend/.env`，填 MySQL 连接。
3. **建库与账号**：确保 MySQL 已建好并授权；在 `backend/` 运行 `python -m app.cli init-db` 建立 15 张表，再运行 `python -m app.cli create-user` 创建演示账号。
4. **起后端**：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
5. **起前端**：在 `frontend/` 运行 `npm ci`、`npm run dev -- --host 127.0.0.1`，打开 http://127.0.0.1:5173/ ，使用刚创建的账号登录。
6. **走通链路**：数据收集 → 保存数据集 → 清洗 → 训练 → 保存模型 → 预测 → 保存结果 → 评估。只有点击「保存到数据库」才会写入业务数据。

旧 7 表 / 12 表数据库不会被自动迁移；请在隔离库用 `infra/schema.sql` 重建。

## 二、关键环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | — | MySQL 连接 |
| `DB_TEST_NAME` | `jit_test` | pytest 专用测试库 |
| `GITHUB_TOKEN` / `GITEE_TOKEN` | 空 | 平台接口凭证，可选，仅提高限额；页面不要求填写 |
| `MODEL_DIR` | `temp/models` | 模型文件根目录 |
| `SEMANTIC_EMBEDDINGS` | 空 | 可选离线语义向量缓存目录 |
| `SEMANTIC_TEXT_MODEL` | 空 | 本地 CodeBERT-base 权重目录或标识 |
| `SEMANTIC_MAX_LEN` | `512` | 语义编码截断长度 |

- 不提供 `API_TOKEN` / `X-API-Key`；鉴权走登录会话。
- 不提供 `SOURCE_REPO` / `SYNC_*`；仓库由收集任务参数指定。

## 三、测试

```bash
cd backend && python -m pytest -q
cd frontend && npm run test:unit
cd frontend && npm run build
cd frontend && npm run lint
python -m pytest -q infra/tests
```

## 四、约定与边界

- **建表**：唯一真源是 `infra/schema.sql`；`docs/数据库/` 与之一致。
- **保存**：数据集、模型、预测结果、评估历史只在用户主动点击「保存到数据库」时入库；执行、预览、导出、刷新都不入库。
- **输入校验**：外部 CSV / Excel 逐列校验列名、顺序与数量；缺列、多列、列序不符直接拒绝。预测输入仅允许缺 `bug`。
- **模型格式**：sklearn 为 `.pkl`，dnn / tabnet 为单文件 `.pt`；下载扩展名跟随 `model_artifact.format`。
- **产物**：统一落 `temp/`，规则见 [docs/约束/artifacts.md](docs/约束/artifacts.md)。
- **口令**：课程演示按明文存储与比对，禁止用于生产环境。
- **历史文件**：`openspec/` 与旧版 README / 部署说明只作追溯，不作为实现依据。

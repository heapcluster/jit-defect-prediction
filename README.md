# 即时软件缺陷预测（JIT Defect Prediction）Web 系统

基于提交级特征（Kamei 14 项）预测代码变更引入缺陷的风险，提供风险列表、提交详情、趋势看板与模型表现四个页面。

本文件是**仓库唯一入口**：容器怎么起、本机怎么跑、测试怎么执行、文档去哪找，都从这里出发。

## 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL 8.0
- 前端：Vue 3 + Vite
- 模型线：Python（scikit-learn / XGBoost / LightGBM / CodeBERT）

## 目录

| 目录 | 说明 |
|---|---|
| `backend/` | FastAPI 应用与 pytest 用例 |
| `frontend/` | Vue 3 单页应用与 vitest 用例 |
| `data_model/` | 数据准备、训练、评测 |
| `infra/` | 建表 DDL、CI 路径选择、nginx 配置，见 [infra/deployment.md](infra/deployment.md) |
| `docs/` | 技术文档（api / database / model / web_page / test） |
| `openspec/` | 规格与变更提案 |

## 一、容器一键启动（推荐先跑通这个）

```bash
docker compose up --build
```

- 前端：http://localhost:8080
- 后端：http://localhost:8000/api/health
- MySQL：localhost:3306（库 `jit_demo`，账号 `jit` / 口令 `jit`，仅本机演示）

自检：

```bash
curl http://localhost:8000/api/health -H "X-API-Key: dev-token"
# 期望 {"code":0,"message":"ok","data":{"status":"...","db":"up",...}}
```

容器化细节（环境变量、插件式扩模型/扩特征、交付边界）见 [infra/deployment.md](infra/deployment.md)。

## 二、本机开发（不用容器）

以下顺序与「可复现」一一对应。个人密码、令牌和仓库绝对路径只写本机未跟踪的 `.env`，不写入 PR。

1. **准备环境**：`conda env create -f data_model/environment.yml`（已有环境可跳过），再 `conda activate jit-defect-prediction`。前端需符合 `frontend/package.json` 的 Node 版本要求。
2. **配置后端**：`cp backend/.env.example backend/.env`，填 MySQL `jit_demo` 的账号与密码。要同步实时提交时填 `SOURCE_REPO`（目录须含 `.git`）。`MODEL_DIR` 留空时回落到仓库内 expert 权重目录，但权重本体需另行取得并核对，不在 Git 中。
3. **起数据库与后端**：确保 MySQL 已建好并授权 `jit_demo`；在 `backend/` 运行 `python -m app.db init` 建立现行五表，再运行
   `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
   旧七表库不会被 `create_all` 自动迁移，应在隔离库重建并验证。建表真源是 `infra/schema.sql`。
4. **起前端**：`cp frontend/.env.example frontend/.env.local`，确保 `VITE_API_KEY` 与后端 `API_TOKEN` 相同；在 `frontend/` 运行 `npm ci`、`npm run dev -- --host 127.0.0.1`，打开 http://127.0.0.1:5173/ 。
5. **走通链路**：先查公开的 `GET /api/health`，再带 `X-API-Key: <本机 API_TOKEN>` 查 `GET /api/models`；本地 Git 源可用时从页面触发同步，或带同一请求头调用 `POST /api/sync`。该接口异步返回，随后轮询 `GET /api/sync/status`，确认 `running=false`、`last_error` 为空，再查询 `/api/commits`。**无数据与同步失败要分开记录。**

## 三、关键环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `API_TOKEN` | `dev-token` | 鉴权令牌；前端构建期注入 `VITE_API_KEY`，两者须一致 |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | — | MySQL 连接 |
| `DB_TEST_NAME` | `jit_test` | pytest 专用测试库 |
| `MODEL_DIR` | `data_model/pipelines/expert/models` | 在线模型目录（含 `feature_order.txt`） |
| `SOURCE_REPO` | 空 | 历史 git 仓库路径；不配则 `/api/predict` 无法现算新提交特征 |
| `SYNC_ON_STARTUP` | `0` | `1` = 启动时后台同步一次最新提交 |
| `HIGH_RISK_THRESHOLD` / `MID_RISK_THRESHOLD` | `0.5` / `0.2` | 高/中风险阈值 |

## 四、测试

```bash
cd backend && python -m pytest -q                              # 后端单测（testpaths = tests）
cd data_model && python -m pytest -q                           # 模型线单测
cd frontend && npm run test:unit -- --coverage                 # 前端 vitest
python -m pytest -q infra/tests                                # CI 契约与建库脚本自测
```

手工执行的黑盒脚本（集成 / 安全 / 压测 / 异常）在 `backend/scripts/`，需要活服务与本机 MySQL，**不进 pytest**；说明见各脚本头部 docstring。

## 五、约定与边界

- **建表**：唯一真源是 `infra/schema.sql`；`data_model/evaluation/out/schema.sql` 副本已下线，不再生成。
- **模型性能指标**：`data_model/evaluation/out/model_metrics.csv` 是 25 个模型在测试集上的指标，**必须入库**（前端「模型性能看板」抽屉依赖）。
- **测试代码**：唯一真源在各端 `tests/` 与 `backend/scripts/`；`docs/test/` 只放文档与证据，不存放代码副本。
- **密钥与权重**：`.env`、`*.pkl`、数据集、`data_model/data/camel` 克隆一律不入库；模型清单（`feature_order.txt` / `manifest.txt` / `load_manifest.txt`）必须入库。
- MySQL 建库授权、真实权重、浏览器截图及运行日志须由实际操作者留证；本文件不宣称这些步骤已在当前机器通过。

# 即时软件缺陷预测（JIT Defect Prediction）Web 系统

基于提交级特征（Kamei 14 项）预测代码变更引入缺陷的风险，顶级导航为数据管理、收集、清洗、训练、预测、评估、解释、定位及修复八个功能 tab。风险列表、趋势和提交详情归入预测，模型性能归入评估；工具间通过文件交换，不要求按顺序运行。

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
| `docs/` | 技术文档（api / database / common / function_point / test / web_page） |
| `openspec/` | 现行规格与活跃变更提案（历史归档不入库） |
| `temp/` | 唯一过程数据根：请求输入、缓存、运行日志、临时文件和 `outputs/<job_id>/` 产物；Git 不追踪，不存源码 |

### 包结构与命名规范

目标：清晰分层、边界可验证、核心功能不变。约束：API 路径、CLI 入口、测试路径与 handoff schema 保持不变；外部调用只走各层公开入口。

- `backend/app/api/`：只做 HTTP 路由与请求校验，薄层；业务编排在 `services/`。
- `backend/app/services/`：按功能命名的编排服务（`*_run.py` 为作业入口，`storage.py` / `output_store.py` / `file_contracts.py` 为共享内核）。
- `data_model/preparation/`：`collect` / `clean` / `public_load` 三个公开入口；`01_*`~`05_*` 为 collect 内部阶段实现，编号体现流水线顺序，外部不直接调用。
- `data_model/pipelines/`：`expert/` 与 `semantic/` 两条模型线；`train.py` 为两线共用的 W5 训练核心。
- `data_model/evaluation/`：评估、指标与图集；`infra/`：DDL、迁移与部署配置。

预期成果：新增功能先按上述分层归位；跨层依赖通过文件契约与公开入口，不直接 import 对方内部模块；`git status` 不因过程数据产生变更噪音。

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
3. **起数据库与后端**：确保 MySQL 已建好并授权 `jit_demo`；在 `backend/` 运行 `python -m app.db init` 建立现行 12 表（现有 5 + 重构新增 7；新增表 DDL 已入 `infra/schema.sql`，迁移脚本与「空库/旧库/重复执行」三冒烟押代码波次），再运行
   `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
   旧七表库不会被 `create_all` 自动迁移，应在隔离库重建并验证。建表真源是 `infra/schema.sql`。模型性能图集由后端启动时自动从 `data_model/pipelines/{line}/reports/figs_by_model/` 补齐到 `backend/static/figures/`（该目录不入库），无需手工拷贝。用户配置落 `user_config` 表，重启后由配置接口恢复；`.env` 阈值仅作出厂默认值（见 `docs/database/user_config.md`）。
4. **起前端**：`cp frontend/.env.example frontend/.env.local`，确保 `VITE_API_KEY` 与后端 `API_TOKEN` 相同；在 `frontend/` 运行 `npm ci`、`npm run dev -- --host 127.0.0.1`，打开 http://127.0.0.1:5173/ 。
5. **走通链路**：先带 `X-API-Key: <本机 API_TOKEN>` 查 `GET /api/health`（三条健康探针都要鉴权，不带 token 返回 401），再查 `GET /api/models`；本地 Git 源可用时从页面触发同步，或带同一请求头调用 `POST /api/sync`。该接口异步返回，随后轮询 `GET /api/sync/status`，确认 `running=false`、`last_error` 为空，再查询 `/api/commits`。若已有同步在跑，第二次触发返回 `40001` +「同步进行中，请稍候」，前端会接上轮询而不再报服务异常。**无数据与同步失败要分开记录。**

## 三、关键环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `API_TOKEN` | `dev-token` | 鉴权令牌；前端构建期注入 `VITE_API_KEY`，两者须一致 |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | — | MySQL 连接 |
| `DB_TEST_NAME` | `jit_test` | pytest 专用测试库 |
| `MODEL_DIR` | `data_model/pipelines/expert/models` | 在线模型目录（含 `feature_order.txt`） |
| `SOURCE_REPO` | 空 | 历史 git 仓库路径；重构后降级为默认仓库（收集任务可显式指定）；不配且任务未指定则 `/api/predict` 无法现算新提交特征 |
| `SYNC_ON_STARTUP` | `0` | `1` = 启动时后台同步一次最新提交 |
| `HIGH_RISK_THRESHOLD` / `MID_RISK_THRESHOLD` | `0.5` / `0.2` | 高/中风险阈值**出厂默认值**；运行期权威 = `user_config`（配置 API / 设置页可改，重启恢复） |

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
- **测试代码**：唯一真源在各端 `tests/` 与 `backend/scripts/`；`docs/想到什么取什么/` 只放文档与证据，不存放代码副本。
- **密钥与权重**：`.env`、`*.pkl`、数据集、`data_model/data/camel` 克隆一律不入库；模型清单（`feature_order.txt` / `manifest.txt` / `load_manifest.txt`）必须入库。
- MySQL 建库授权、真实权重、浏览器截图及运行日志须由实际操作者留证；本文件不宣称这些步骤已在当前机器通过。

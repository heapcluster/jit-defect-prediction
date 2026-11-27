# 项目包结构设计

一句话：把"预测单仓库 + 后续叠加的 Web 工具台"收敛为"内核独立、配置单一权威、API 按页面分组、产物归属明确"的分层结构；本文定义配置收敛、`core/` 分层、`localize` 任务语义、前端 API 分组、算法资产归属五件事。

实现状态：部分（前端 API 分组已实施；`core/`、`infra/`、`config_schema.py` 为目标（未实施），文中已逐项标注）。

## 0. 范围与边界

**本文负责**：
- 配置来源分层与出厂默认单一真源
- `backend/app/core/` 与 `backend/app/infra/` 分层（目标）
- `localize` 的任务/同步语义统一
- 前端 API 按页面分组
- `data_model/` 算法资产与后端运行时产物的归属

**本文不涉及**：单个接口的字段与错误码（见 `docs/api/`）、单表 DDL 与字段（见 `docs/database/`）、页面交互与验收（见 `docs/web_page/`）；这些对象以各自文档为准。

## 1. 目标结构

```text
jit-defect-prediction/
├── backend/
│   └── app/
│       ├── api/              薄路由：一个页面/资源一个文件，只做校验与编排
│       ├── services/         业务用例与任务 worker：可落库、可发布产物
│       ├── core/             【目标（未实施）】纯算法内核：无 DB、无 job、无 FastAPI 依赖
│       │   ├── localization.py   ← 原 localization_core.py
│       │   ├── explain.py        ← 原 explain_core.py
│       │   ├── model_registry.py ← 原 model_registry.py
│       │   ├── feature_source.py ← 原 feature_source.py
│       │   └── semantic_source.py← 原 semantic_source.py
│       ├── infra/            【目标（未实施）】基础设施：DB、配置、 schema、时间
│       │   ├── config.py        ← 原 app/config.py（仅部署/env）
│       │   ├── db.py
│       │   ├── models.py
│       │   ├── schemas.py
│       │   └── timeutil.py
│       ├── config_schema.py  【目标（未实施）】配置键 schema + 出厂默认单一真源
│       ├── main.py
│       └── cli.py
├── frontend/
│   └── src/
│       └── api/
│           ├── request.js        公共请求与鉴权
│           ├── collect.js  clean.js  train.js  predict.js
│           ├── evaluate.js  figures.js  explain.js  localize.js
│           ├── storage.js  datasets.js  models.js  sync.js
│           ├── jobs.js  config.js  commits.js
│           └── index.js          仅汇总 re-export
├── data_model/               算法交付资产（.pkl/.npz/图/报告），后端只读消费
├── infra/                    DDL 与迁移脚本
└── docs/                     具体设计文档，不设索引类文档
```

现状：`app/` 已有 `api/` 与 `services/` 分层，顶层 `config.py`、`db.py`、`models.py`、`schemas.py`、`timeutil.py` 与算法模块仍在 `app/` 根；`core/`、`infra/`、`config_schema.py` 为已定型但尚未实施的目标结构。

分层约束：
- `api/` 不写业务规则，不直接 import `core/`；只调 `services/`。
- `services/` 可 import `core/` 与 `infra/`，负责 `job`、`output_store`、`config_store` 的编排。
- `core/` 是纯函数/类：接口只吃数据与配置，不接 `Session`、不写文件、不读 env。这样可脱离 Web 独立测试与复用。
- `infra/` 只描述"怎么连、表长什么样、时间怎么格式化"，不含业务判断。

## 2. 配置收敛

### 2.1 三类配置来源

| 类别 | 权威位置 | 内容 | 是否用户可调 |
|---|---|---|---|
| 部署 / 密钥 | 环境变量 + `.env`（`infra/config.py` 读取） | DB 连接、`API_TOKEN`、路径根、LLM、`SYNC_*` | 否，运维设置 |
| 运行期配置 | `user_config` 表 + `config_store.py` | 阈值、指标、页面偏好、采集白名单、定位权重、模板等 | 是，设置页或 API 读写 |
| 算法出厂参数 | `data_model/*/config.py` | 训练 seed、模型清单、`DECISION_THRESHOLD`、图目录等 | 否，算法资产自带 |

硬规则：
- **出厂默认单一真源**：`config_schema.py` 的 `CONFIG_SCHEMA` + `FACTORY_DEFAULTS`（由现 `config_store.py:21-80` 迁入）。任何模块不得另写一份默认值。
- `infra/config.py` 只放**没有环境就无意义**的值（连接串、密钥、路径），不放 `HIGH_RISK_THRESHOLD` / `MID_RISK_THRESHOLD` 这类用户可调阈值——它们搬进 `FACTORY_DEFAULTS`。
- `data_model/*/config.py` 中的 `DECISION_THRESHOLD=0.5` 只作为**离线训练默认**，在线运行阈值一律来自服务层或本次请求，不反向覆盖运行期配置。
- `selected_model` 仅页面回显，不参与任何运行入口；模型必须由每次运行显式指定。

### 2.2 目标迁移清单（未实施）

| 现位置 | 现状 | 目标 |
|---|---|---|
| `services/config_store.py:21-80` | schema + 默认值 | 迁到 `config_schema.py`，`config_store.py` 只保留读写/校验逻辑 |
| `app/config.py:132-134` | `HIGH/MID_RISK_THRESHOLD` 从 env 读 | 删除；默认值进 `FACTORY_DEFAULTS`，env 仅可作为出厂默认覆盖（可选兼容） |
| `app/config.py:139` `MODEL_METRICS_CSV` | 全后端无消费方 | 删除（或标注为算法资产只读路径，非运行配置） |
| `services/train_run.py:102-111`、`predict_run.py:109-118`、`evaluate_run.py:54-59` | 阈值/指标硬编码或分散读取 | 统一经 config_schema；阈值按运行提交，不写回全局 |
| `services/explain_run.py:103` | `top_n=8`、`cache_ttl=3600` 硬编码 | 进 `FACTORY_DEFAULTS`（`explain.top_n` 新增键） |
| `localization_core.py:27-28,92-95` | 权重与 `file_size_max` 默认副本 | 只从 `config_schema` 取，不自带常量 |
| `.env.example:46-50` | 风险阈值 | 移除或改为"仅覆盖出厂默认"的显式说明 |
| `frontend/src/utils/thresholds.js:17-28` | 消费 `ui.background_color`/`ui.accent_color` | 删除颜色读取；设置页已不展示颜色，键保留在配置表但不被前端消费 |
| `frontend/src/utils/thresholds.js` | 本地阈值 fallback | 保持现状：只用服务端完整 schema，不本地兜底 |

### 2.3 阈值写入口径

- `decision_threshold`：预测页默认 `0.5`，按本次运行显式提交；写入 `job.params_json`、summary 与 `prediction` 表，不写回全局配置覆盖后续运行。
- `risk_high_threshold` / `risk_mid_threshold`：全局风险等级配置，只影响展示，写 `user_config`。
- 评估不读取阈值配置：`predicted_label` / `decision_threshold` 从预测结果透传。

## 3. `core/` 分层迁移（目标）

下列迁移为已定型目标，尚未实施。

| 现文件 | 目标 | 依赖清理 |
|---|---|---|
| `app/localization_core.py` | `app/core/localization.py` | 去掉 `from app import config_store` 与 `DEFAULT_WEIGHTS` 副本，改为由 `services/localize_run.py` 传入配置 |
| `app/explain_core.py` | `app/core/explain.py` | 保持纯技术目录/兼容矩阵，不读 DB |
| `app/model_registry.py` | `app/core/model_registry.py` | 模型路径由参数传入，不从 `config.py` 直接取 |
| `app/feature_source.py` | `app/core/feature_source.py` | 特征列定义在 core，仓库路径由参数传入 |
| `app/semantic_source.py` | `app/core/semantic_source.py` | embedding 路径由参数传入 |
| `app/config.py` / `db.py` / `models.py` / `schemas.py` / `timeutil.py` | `app/infra/` | 仅移动，不改行为 |

迁移纪律：
- 先加 `core/`、`infra/` 并保留旧路径的 re-export 兼容层，再逐个切换 import，最后删除兼容层。
- `core/` 模块不得出现 `from app.services import ...`、`from app.models import ...`、`Session` 参数；发现即为分层违规。
- `core/` 的测试不启动 FastAPI、不连数据库。

## 4. `localize` 任务语义

现状不一致：
- `output_store.MODULES` 含 `"localize"`，会发布定位产物并登记 `job_id`。
- `job_store.KINDS = (collect, clean, train, predict_batch, evaluate, explain)`，无 `localize`。
- `services/localize_run.py:131-142` 生成 `job_id` 并发布产物，但不创建 `Job` 行，也不走任务状态机。
- 前端把定位当独立动作调用，产物模块也登记了 `localize` 产物。

目标设计（选定"同步产物"口径）：
- 缺陷定位及修复是**预测详情页内的同步板块**：`POST /api/localize/run` 同步执行、同步返回，不进任务中心、不显示进度、不支持取消/重试。
- `localize_run.py` 生成的 `job_id` 只作为**产物批次标识**，用于 `output_store` 发布和 `localization_evidence_<job_id>.json` 命名；它不是 `job` 表行，禁止在 API 响应用 `job_id` 字段暗示可轮询任务状态。
- `job_store.KINDS` 不加 `localize`；`/api/jobs` 不返回定位记录。
- `output_store.MODULES` 保留 `localize`，产物照常登记、可下载、可 pinn 到产物库。
- 接口映射维持：`predict_detail.md` → `POST /api/localize/run`、`GET /api/source/tree`、`GET /api/source/file`。批量定位 `POST /api/explain/run` 同理属 API/CLI 能力，不做 Web 任务。

若后续要支持大仓库异步定位，必须作为**新需求**引入 `localize` kind、任务状态机与页面进度，不能把当前同步产物伪装成任务。

## 5. 前端 API 分组

`frontend/src/api/index.js` 原先把 15 组接口集中在一个文件。目标按 `web_page/` 页面 + 少量共享资源拆分：

| 文件 | 归属页面 | 主要函数 |
|---|---|---|
| `collect.js` | 数据收集 | `runCollect`、`getCollectBranches`、`getCollectSourceColumns`、`resaveCollect`、`getCollectPreview`、`fetchCollectOutput` |
| `clean.js` | 数据清洗 | `getCleanOperations`、`runClean`、`getCleanPreview`、`fetchCleanOutput` |
| `train.js` | 模型训练 | `getAlgorithms`、`runTrain`、`fetchTrainOutput` |
| `predict.js` | 模型预测 | `postPredict`、`runPredict`、`getPredictPreview`、`fetchPredictOutput` |
| `evaluate.js` | 预测评估 | `getEvaluateMetrics`、`runEvaluate`、`fetchEvaluateOutput` |
| `figures.js` | 模型性能页 | `getFigures`、`fetchFigureBlob` |
| `commits.js` | 预测详情页 | `getCommits`、`getCommitDetail` |
| `explain.js` | 详情页解释板块 | `getExplainTechniques`、`postExplain`、`runExplain`、`fetchExplainOutput` |
| `localize.js` | 详情页定位板块 | `getSourceTree`、`getSourceFile`、`runLocalize`、`fetchLocalizeOutput` |
| `storage.js` | 数据存储 | `importStorageFiles`、`exportStorageTable`、`getStorageLineage`、`deleteStorageChain`、`fetchStorageOutput` |
| `datasets.js` | 数据共享 | `getDatasets`、`getDatasetCommits`、`exportDataset`、`deleteDataset` |
| `models.js` | 模型加载 | `getModels`、`getModelsStatus`、`loadModel`、`unloadModel`、`reloadModel`、`setSelectedModel` |
| `jobs.js` | 任务中心共享 | `getJobs`、`getJob`、`retryJob`、`cancelJob` |
| `config.js` | 系统设置 | `getConfig`、`putConfig`、`putConfigKey`、`deleteConfigKey` |
| `sync.js` | 数据同步 | `postSync`、`getSyncStatus` |
| `request.js` | 共享 | 统一鉴权、错误码、二进制下载、storage 响应选项 |
| `index.js` | 汇总 | 仅 re-export，不含实现 |

约束：
- 页面组件只从对应分组文件或 `index.js` 汇总导入，不在组件内手写 `fetch`。
- 二进制下载统一走 `request.js` 的带 `X-API-Key` fetch + ObjectURL，不打开免鉴权 URL。

## 6. 算法资产归属

```text
data_model/                    算法交付资产（只读、可重建）
├── preparation/               收集 / 特征工程脚本
├── pipelines/
│   ├── expert/  semantic/     训练脚本、models/*.pkl、data/*.npz、reports/
│   └── evaluation/            指标公式、model_metrics.csv、报告
└── environment.yml            算法环境（可与后端不同）
backend/                       运行时服务（消费算法资产，不拥有）
├── static/figures/            从 data_model 图集同步的展示副本（可重建，不入库）
└── app/                       代码；temp/ 下运行时产物不入库
infra/                         DDL 与迁移
```

归属规则：
- `.pkl`、`.npz`、`figs_by_model/*.png` 归 `data_model/`，是算法产物；后端 `MODEL_DIR`、`SEMANTIC_EMBEDDINGS` 指向它们，只读消费。
- `backend/static/figures/` 是展示副本，由 `figure_store.sync_figures()` 从 `data_model` 同步；可随时重建，不入库。
- `temp/outputs/<job_id>/` 是运行时产物，不入库；`output_store` 统一发布/manifest/checksum。
- Docker 以只读卷挂载 `data_model/pipelines/*/models` 到后端 `/models`；后端不写算法资产目录。
- 训练产出新模型时，先写 `data_model` 算法目录并登记 `model_artifact`，后端通过 `model_name` 加载，不做隐式回退。

### 6.1 各阶段产物落点表

所有 Web 工具阶段的主产物都落 `temp/outputs/<job_id>/`，由 `output_store.publish_output()` 统一发布（原子落盘 + manifest + checksum），下载端点统一 `GET /api/{module}/outputs/{job_id}/{name}`。各阶段文件名：

| 阶段 | 主产物（模块前缀） | 落点 | 内部记录 |
|---|---|---|---|
| 数据收集 | `collected_commits_<job_id>.csv` | `temp/outputs/<job_id>/` | manifest / summary / audit / quality |
| 数据清洗 | `clean_dataset_<job_id>.csv` 或 `<output_name>.csv` | 同上 | manifest / steps_stats（前后差异） |
| 模型训练 | `train_trainset_<job_id>.csv`、`train_testset_<job_id>.csv`、逐算法 `.pkl` | 训练集 / 测试集落 outputs；`.pkl` 落 `data_model/pipelines/*/models/` 并登记 `model_artifact` | manifest；模型元数据为内部文件，不登记为用户产物 |
| 模型预测 | `predict_predictions_<job_id>.csv` 或 `<output_name>.csv` | `temp/outputs/<job_id>/`；完整行同时 upsert 到 `prediction` 表 | manifest / summary |
| 预测评估 | `<figure_zip_name>.zip`、`<metrics_name>.csv/.xlsx` | 同上；逐图另登记 `model_figure` 并同步展示副本到 `backend/static/figures/` | manifest / summary / 逐图；内部指标长表与混淆矩阵不展示 |
| 预测结果解释 | `explain_explanations_<job_id>.csv/.xlsx` | `temp/outputs/<job_id>/` | manifest / 对比 / 贡献图 |
| 缺陷定位及修复 | `localization_localization_<job_id>.csv/.xlsx`、`localization_evidence_<job_id>.json`、`localization_suggestions_<job_id>.md` | 同上（同步产物，无 `job` 行） | manifest |

说明：
- `model_figure` 逐图同步展示副本时，文件名按 `evaluate_<job_id>_<figure_type>.png` 标准命名（字段与索引见 `docs/database/model_figure.md`）。
- 训练产物 `.pkl` 不在 `temp/outputs/`，而是在 `data_model/` 算法目录——这是唯一跨越"运行时产物"与"算法资产"的例外，因为它需要长期保留与版本化。
- `output_store.MODULES` 含 `localize` / `datasets`，但 `job_store.KINDS` 不含它们：下载走统一端点，任务中心不展示。

## 7. 验收

- `core/` 模块无 DB / FastAPI / env 依赖，可独立导入与测试。
- 配置默认值全仓库仅在 `config_schema.py` 定义一处；`grep` 不到第二份 `decision_threshold=0.5` 作为运行期默认。
- 风险阈值不再从 `.env` 读；前端不消费 `ui.background_color` / `ui.accent_color`。
- `/api/jobs` 不返回 `localize` 记录；`localize` 产物仍可下载、可在产物库查到。
- 前端 API 按分组文件存在，组件内无裸 `fetch`。
- 后端容器不写 `data_model/`；删除 `backend/static/figures/` 后重启可由 `data_model` 重建。
- 文档与代码不一致时，以本文与 `docs/overview.md` 为准：先改文档、再改代码，不让实现反向改写设计目标。

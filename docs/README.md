# 技术文档索引与产品边界

- **文档形态**：目标契约。每篇头部单行标 `实现状态：已实现|部分|未实现` 与 `期次：一期|二期`，作为实现进度台账；契约本身不描述旧实现。
- **权威关系**：需求输入为 [`../TODO/00-重构说明与开发执行要求.md`](../TODO/00-重构说明与开发执行要求.md) 至 `TODO/09` 与需求图片；本目录是重构后的设计契约。代码滞后于契约时以契约为准推进实现，不得反向把现状写回契约。
- 仓库运行入口见 [`../README.md`](../README.md)。本索引不另立第二份契约，口径以对象文件为准。

## 目录

- [模块间文件契约](file-contracts.md)：**交换文件单一权威**（列 schema / 编码 / manifest / fixtures），比表契约更前置。
- [API](api/)：17 组端点（八模块文件运行 + 存储导入导出 + 读/管理/配置/任务）。
- [数据库](database/)：12 张表的字段与约束；表是展示与持久化层，不是模块间总线。
- [功能点](function_point/)：八个独立工具模块 + 拓展的职责、文件输入输出与验收。
- [页面](web_page/)：8 个功能 tab（与原图功能①~⑧一一对应，展示与配置收进对应 tab 内子视图）的交互契约与 ASCII 线框。
- [模型卡片](model/)：25 个模型的训练配置与工件登记契约。
- [测试](想到什么取什么/)：冻结轮次的测试计划、交付物与实测证据（历史证据，不随契约改写）。
- [公共文档](common/)：课程要求与考核说明、测试口径。

## 1 产品目标

系统以 Git commit 为单位给出缺陷风险、解释、可疑行定位与修复建议。**功能 1–8 是八个可独立验收 / 测试 / 运行的工具，不是一条连贯流水线**：在任一功能点上传它该吃的输入文件（CSV/XLSX），即可拿到它该吐的输出文件；上下游模块在不在场都无所谓。模块间握手 = 交换文件 + JSON manifest（见 [file-contracts.md](file-contracts.md)）；数据库只承担可选展示导入、配置与任务状态持久化。Web 工具台、CLI、API 调用同一实现；在线全链路串跑仅为可选演示编排，不是任何模块的验收前提。功能 9（独立客户端、VS Studio / Eclipse 插件、CI/CD、提交事件触发）是前八项验收后的封装拓展。

**门禁口径**：默认建议模式，不阻断合并；显式开启严格模式时可按阈值阻断（功能 9 配置项）。

## 2 模块清单

| 功能 | 模块 | 契约 | 独立运行端点（文件进→文件出） | 实现状态 |
|---|---|---|---|---|
| 1 | 数据库存储与配置中心 | [storage](function_point/storage.md) | `POST /api/storage/import`、`GET /api/storage/export`、`/api/config` 族 | 部分 |
| 2 | 缺陷数据收集 | [collect](function_point/collect.md) | `POST /api/collect/run` | 已实现 |
| 3 | 数据清洗与预处理 | [clean](function_point/clean.md) | `POST /api/clean/run`、`GET /api/clean/operations` | 已实现 |
| 4 | 模型训练 | [train](function_point/train.md) | `POST /api/train/run`、`GET /api/algorithms` | 已实现 |
| 5 | 模型预测 | [predict](function_point/predict.md) | `POST /api/predict/run`、`POST /api/predict`（单条）、`/api/models` 族 | 已实现 |
| 6 | 预测性能评估 | [evaluate](function_point/evaluate.md) | `POST /api/evaluate/run`、`GET /api/evaluate/metrics` | 已实现 |
| 7 | 预测结果解释 | [explain](function_point/explain.md) | `POST /api/explain/run`、`POST /api/explain`、`GET /api/explain/techniques` | 已实现 |
| 8 | 缺陷定位及修复 | [localization](function_point/localization.md) | `POST /api/localize/run`、`GET /api/source/tree\|file` | 已实现（无可靠修复补丁时只交付建议） |
| 9 | 多种形态拓展 | [extension](function_point/extension.md) | 统一分析内核 CLI / 容器（吃上述文件组合） | 二期 |

输出下载统一 `GET /api/{module}/outputs/{job_id}/{name}`；异步任务统一 `/api/jobs` 族（六类 kind、五态、重试、取消）；读类接口（commits/trends/figures/models/health）只读，供展示页消费导入后的库。

## 3 数据边界

**模块间数据 handoff = 交换文件**（commits / cleaned / model_package / predictions / labels / metrics / explanations / localization + manifest），schema 单一权威见 [file-contracts.md](file-contracts.md)。关系库 12 表：`commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit`，角色 = 展示导入 + 配置 + 任务状态 + 资产登记；建表真源 [`../infra/schema.sql`](../infra/schema.sql)（DDL 与 ORM 已同步），逐表见 [`database/`](database/)。一期不动现有主键；数据集多版本属二期。公开 JIT 缺陷数据集（课程附加 3）落盘独立文件 + 元数据，不入库，契约见 [function_point/collect.md](function_point/collect.md) §9。

## 4 模型边界

四条模型线 expert / semantic / fused / e2e，报告口径 25 个模型，满足课程「至少 2 类（经典机器学习 + 深度学习）、不少于 8 种预测模型」硬要求（类别对照见 [function_point/train.md](function_point/train.md) §3）。**模型名单唯一登记源 = `model_artifact`**，`model` 行由其派生；独立运行路径下模型以 `model_package.zip` 文件交付与加载（checksum 校验），登记入库为可选展示路径。默认模型 = `user_config.default_model`，未配置时回退「已加载 expert 中 version_key 最大者」。算法与超参数 schema 登记于 `algorithm` 表，训练表单不硬编码。

指标公式单源 = 新增 `data_model/evaluation/metrics.py`（收敛现 `evaluation/figures.py:46-57` 与四线 `pipelines/*/metrics.py`）；评估是独立工具：输入 predictions + 标签文件 + 阈值/指标配置，产出 metrics / 混淆 / 图 / 报告文件；默认 0.5 下与历史 `model_metrics.csv` 逐值一致作为口径一致性验收线。评估只有单一文件化运行口径，结果永远对应某次显式运行，配置变更不产生隐式自动重算。

## 5 页面与交付

8 个功能 tab 与原图功能①~⑧一一对应，展示页与设置收进对应 tab 内子视图（风险列表/趋势/详情→⑤，模型性能→⑥，设置→①）；旧链接保留并归入对应功能，交互契约与 ASCII 线框见 [`web_page/`](web_page/)。工具台 = 上传输入文件 → 配置 → 运行 → 输出预览 + 下载；支持展示映射的产物可选导入库，定位只交付文件。展示子视图不承载业务计算、不作为模块运行前置。图片一律带 `X-API-Key` fetch 转 ObjectURL。部署、密钥和权重投放见 [`../README.md`](../README.md) 与 [`../infra/deployment.md`](../infra/deployment.md)。

## 6 本机运行提示

- **代理**：终端或 `backend/.env` 配了 `HTTP_PROXY` / `HTTPS_PROXY` 时必须同时设 `NO_PROXY=127.0.0.1,localhost`，否则连本机 8000 也走代理被拒；脚本侧可用 `httpx.Client(trust_env=False)` 兜底。
- **同步离线**：`SYNC_FETCH=0` 时收集跳过 `git fetch`，直接用源仓库本地 HEAD，适合固定版本/断网演示。
- **一句话风险总结**：`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 配置后由 LLM 生成；缺任一项或失败回退模板句，不影响详情/预测。Key 只写本机 `.env`，不入库。
- **数据留证**：离线测试数据与实时收集结果分别留证，不互相冒充；真实数据库、权重和页面验收由实际操作者执行并记录。
- **网络受限**：本机到 GitHub 的 HTTPS 与大 pack SSH 传输可能不可用；收集模块一期验收以本地仓库路径为准，URL 采集验收须在网络可用环境执行并留证。

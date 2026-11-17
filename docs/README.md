# 技术文档索引与产品边界

仓库运行入口见 [`../README.md`](../README.md)。本目录按对象保存技术契约；接口或数据口径以对应对象文件为准，本索引不另立第二份契约。

## 目录

- [API](api/)：请求、响应与错误码。
- [数据库](database/)：五张表的字段与约束，以及数据采集/特征链路口径。
- [功能点](function_point/)：业务行为。
- [页面](web_page/)：四个页面的交互。
- [测试](想到什么取什么/)：测试计划、交付物与实测证据。
- [公共文档](common/)：课程要求（`project-requirements.md`）与考核说明（`test-assessment-guide.md`）。

## 1 产品目标

系统以 Git commit 为单位给出建议性缺陷风险，供评审人员排序和查看解释。预测结果不作为合并 PR 的强制门禁。

## 2 在线业务链路

`SOURCE_REPO` 指向本地 Git 历史 → 同步或单条预测抽取 Kamei 14 维特征 → 已加载模型推理 → 写入 MySQL → 风险列表、提交详情、趋势和模型性能四个页面读取。`POST /api/sync` 是异步批量补算入口，`POST /api/predict` 是单条现算入口；详情见 [`api/`](api/) 与 [`function_point/`](function_point/)。

## 3 数据边界

当前关系库为 `commit`、`commit_feature`、`model`、`prediction`、`model_figure` 五表。建表真源是 [`../infra/schema.sql`](../infra/schema.sql)，字段与索引逐表见 [`database/`](database/)。离线评估数据导入只用于明确标记的测试或演示，不等同于实时同步结果。

## 4 模型边界

离线训练与评估覆盖 expert、semantic、fused、e2e 四条模型线，现有报告口径为 25 个模型。在线可选集合取决于实际交付权重及后端注册表；expert 的八项清单见 [`../data_model/pipelines/expert/models/feature_order.txt`](../data_model/pipelines/expert/models/feature_order.txt)。训练模型数不等于已经可在当前机器在线加载的模型数。

### 4.1 数据与训练

离线样本固定版本、时间序切分和 SZZ 标签判据见 [`database/README.md`](database/README.md) 的「数据采集与特征链路」一节。语义特征、融合特征与端到端模型的实施状态须以各线实际产物和测试报告核验。

### 4.2 评估结果

指标和图集以 [`../data_model/evaluation/`](../data_model/evaluation/) 的实际输出及 [`想到什么取什么/`](想到什么取什么/) 的实测证据为准；生成目录不入库时不能把未生成的文件当作已交付证据。

### 4.3 扩展范围

语义特征与公开数据集质量治理的新增承诺须经过独立 OpenSpec change 和验收，不因旧提案存在就视为已完成。待实施项以 `openspec/changes/` 下的活跃 change 为准，已完成的归档在 `openspec/changes/archive/`。

## 5 页面与交付

四个当前页面及其交互见 [`web_page/`](web_page/)；模型性能看板读取测试集评估数据，普通风险列表与实时同步链路分开验收。部署、密钥和权重投放见 [`../README.md`](../README.md) 与 [`../infra/deployment.md`](../infra/deployment.md)。

## 6 本机运行提示

完整运行步骤见仓库根 [`../README.md`](../README.md)。以下是容易踩坑的两点：

- **代理**：若终端或 `backend/.env` 配了 `HTTP_PROXY` / `HTTPS_PROXY`，必须同时设 `NO_PROXY=127.0.0.1,localhost`（`.env.example` 已给出），否则 `httpx` / `requests` 连本机 8000 也会走代理并报连接被拒。脚本侧可用 `httpx.Client(trust_env=False)` 兜底。
- **同步离线**：`SYNC_FETCH=0` 时刷新跳过 `git fetch`，直接使用 `SOURCE_REPO` 的本地 HEAD，适合固定版本/断网演示；需要追踪远端新提交时保持默认 `1`。
- **一句话风险总结**：`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 三项配置后由 LLM 生成（OpenAI 兼容 `/chat/completions`）；缺任一项或调用失败时自动回退模板句，不影响详情/预测。Key 只写本机 `.env`，不入库。
- **数据留证**：离线测试数据与实时同步结果应分别留证，不能互相冒充。真实数据库、权重和页面验收仍须由实际操作者执行并记录。

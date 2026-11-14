# 产品范围与数据流

本文件只记录当前范围和模块边界。运行命令见 [`../README.md`](../README.md)；字段、接口和页面行为以本目录对应对象文件为准。

## 1. 产品目标

系统以 Git commit 为单位给出建议性缺陷风险，供评审人员排序和查看解释。预测结果不作为合并 PR 的强制门禁。

## 2. 在线业务链路

`SOURCE_REPO` 指向本地 Git 历史 → 同步或单条预测抽取 Kamei 14 维特征 → 已加载模型推理 → 写入 MySQL → 风险列表、提交详情、趋势和模型性能四个页面读取。`POST /api/sync` 是异步批量补算入口，`POST /api/predict` 是单条现算入口；详情见 [`api/`](api/) 与 [`function_point/`](function_point/)。

## 3. 数据边界

当前关系库为 `commit`、`commit_feature`、`model`、`prediction`、`model_figure` 五表。建表真源是 [`../infra/schema.sql`](../infra/schema.sql)，字段与索引逐表见 [`database/`](database/)。离线评估数据导入只用于明确标记的测试或演示，不等同于实时同步结果。

## 4. 模型边界

离线训练与评估覆盖 expert、semantic、fused、e2e 四条模型线，现有报告口径为 25 个模型。在线可选集合取决于实际交付权重及后端注册表；expert 的八项清单见 [`../data_model/pipelines/expert/models/feature_order.txt`](../data_model/pipelines/expert/models/feature_order.txt)。训练模型数不等于已经可在当前机器在线加载的模型数。

### 4.1 数据与训练

离线样本固定版本、时间序切分和 SZZ 标签判据见 [`common/data-pipeline.md`](common/data-pipeline.md)。语义特征、融合特征与端到端模型的实施状态须以各线实际产物和测试报告核验。

### 4.2 评估结果

指标和图集以 [`../data_model/evaluation/`](../data_model/evaluation/) 的实际输出及 [`test/`](test/) 的实测证据为准；生成目录不入库时不能把未生成的文件当作已交付证据。

### 4.3 扩展范围

语义特征与公开数据集质量治理的新增承诺须经过独立 OpenSpec change 和验收，不因旧提案存在就视为已完成。待实施项见 [`../openspec/changes/README.md`](../openspec/changes/README.md)。

## 5. 页面与交付

四个当前页面及其交互见 [`web_page/`](web_page/)；模型性能看板读取测试集评估数据，普通风险列表与实时同步链路分开验收。部署、密钥和权重投放见 [`../README.md`](../README.md) 与 [`../infra/deployment.md`](../infra/deployment.md)。

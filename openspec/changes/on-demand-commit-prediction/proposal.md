# 新提交现算特征并在线预测

## Why

原预测接口只读取 `commit` 与 `commit_feature` 表；新提交未入库时返回 40400，无法满足“新提交即可在线预测”。模型线的 `single-commit-feature-extraction` 已提供单条入口，本 change 把它接入后端，并要求详情通过显式 `model_name` 查看所选模型的预测。

## What Changes

- 服务端 `.env` 新增可选 `SOURCE_REPO`，由服务端指定本地 Git 仓库，客户端仍只提交 hash 与可选 model_name。
- 提交/特征缺失时调用模型线单条入口，按现有表字段落库，再实时推理并幂等写 `prediction`。
- 详情按显式 `model_name` 查询所选模型；未指定时使用全站默认模型，不跨模型自动回退；回归测试覆盖新提交、重复调用、来源缺失与哈希规范化。

## Capabilities

### Modified Capabilities

- `predict-api`: 新提交可从配置的仓库现算特征；错误码仍用冻结集合。
- `query-api`: 详情显式指定模型时展示该模型预测；未指定时与列表使用同一默认模型。

## Impact

基于 `single-commit-feature-extraction` 模型线 PR，修改后端配置、预测与详情接口、测试及 `docs/api/README.md`。数据库结构、请求体字段、14 项数值口径不变；本地仓库路径只能在服务端设置。

## 不做什么

不从请求中接收任意仓库路径，不抓取远端 Git，不上传权重/数据集/密钥；不宣称首次全历史扫描或随机森林 SHAP 已达到 500ms p95。前端交互和真实 Camel/数据库演示另行验收。

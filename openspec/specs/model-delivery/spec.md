# model-delivery Specification

## Purpose
把训练产物交付给后端线：模型权重不入库，在线模型集合与特征顺序由 `data_model/pipelines/expert/models/feature_order.txt` 声明，后端按该清单加载；预测数据只由实时同步或在线预测产生。离线评估文件不得作为运行时灌库入口。

## Requirements

### Requirement: `.pkl` 导出的特征顺序 MUST 以现行交付清单为准

expert 在线模型 MUST 序列化为 `.pkl` 落 `data_model/pipelines/expert/models/`（权重被 `.gitignore` 排除，不入库）。

**在线特征顺序的运行时权威是 `data_model/pipelines/expert/models/feature_order.txt` 的 `[feature_order]`**；字段含义与 `docs/database/commit_feature.md` 对照。交付包可包含该清单的副本，但不得另立第二套顺序：

- 交付副本 MUST 与仓库清单逐字一致；不一致时拒绝加载并报告差异
- 字段名或列序变更 MUST 通过 change 同步更新清单、特征表定义与后端加载校验
- 交付副本不构成第二份独立口径，维护判断回到仓库清单与已批准的规格

> 历史交付约定曾同时提到独立契约和随包清单。当前以仓库的 `feature_order.txt` 为运行时清单，旧目录及旧契约文件已移除；历史记录不再作为现行路径使用。

#### Scenario: 后端按清单组装特征
- **WHEN** 后端加载 `.pkl` 并按特征顺序清单构造输入向量推理
- **THEN** 对同一条提交，推理结果与训练侧离线预测一致

#### Scenario: 模型文件不入库（边界场景）
- **WHEN** 交付权重后执行 `git status --short`
- **THEN** `data_model/pipelines/expert/models/` 下的 `.pkl` 权重不出现（被忽略规则排除），不使用 `git add -f`

### Requirement: model_name MUST 按 <算法>_v<序号> 命名

每个模型 MUST 有形如 `<算法>_v<序号>` 的 `model_name`（如 `xgb_v1`，与契约一表三示例一致）；模型迭代 MUST 换新名字，MUST NOT 覆盖旧 `model_name` 的历史结果。

#### Scenario: 命名合法
- **WHEN** 任一模型交付
- **THEN** `model_name` 匹配 `<算法>_v<数字>` 格式，且在同批交付中唯一

#### Scenario: 名字与旧版本冲突（边界场景）
- **WHEN** 新模型沿用了已有 `model_name`（如重训后仍叫 `xgb_v1`）
- **THEN** MUST 换新序号（`xgb_v2`）；MUST NOT 覆盖旧名字 —— 覆盖会让 `prediction` 表里新旧结果混作一批，趋势看板无法解释

### Requirement: 离线预测结果 MUST 与在线入库隔离

模型线可产出 `prediction_result.csv` 用于离线评估；该文件 MUST NOT 被后端服务、启动过程或 CI 当作运行时灌库输入。`prediction` 表由实时同步或在线预测按 `(commit_hash, model_name)` 幂等写入；模型线 MUST NOT 直连运行库。

#### Scenario: 离线文件存在
- **WHEN** 模型线生成离线预测结果文件
- **THEN** 文件可用于评估报告，但运行库仍只由实时同步或在线预测写入，不提供 CSV 灌库入口

#### Scenario: 数据线不碰库（边界场景）
- **WHEN** 审查数据线脚本与依赖
- **THEN** 模型训练与离线预测脚本不连接运行数据库；写库逻辑仅存在于后端线

### Requirement: SHAP 依赖 MUST 随交付清单钉版本

A 方案交付 MUST 含 SHAP 依赖及其版本 pin（写入 `data_model/environment.yml`）。SHAP 实时计算 MUST 满足后端非功能要求（95% 请求 < 500ms），无法满足时 MUST 记录实测数据并提契约变更讨论。

> 契约三「待确认」项（`explanation` 的具体算法）**已由 PR #6 结清为 SHAP**，故本 Requirement 不再含「SHAP 定稿后回填契约」这一动作 —— 那条回填已无对象。

#### Scenario: 交付清单完整
- **WHEN** 后端线接收 A 方案交付
- **THEN** 清单含 `.pkl` 路径、特征顺序清单、SHAP 依赖版本；按清单安装后加载与推理可跑通

#### Scenario: 性能不达标不静默（边界场景）
- **WHEN** SHAP 实时计算使预测接口超过 500ms 分位要求
- **THEN** 实测数据登记进报告与契约变更提案，不得静默降级或换算法不通知后端线

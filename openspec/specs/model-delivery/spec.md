# model-delivery Specification

## Purpose
把模型产物交付给后端：expert 在线权重与 14 维列序随包交付，四线评估图和测试集预测由 `data_model/evaluation/` 生成，数据库结构与当前 `docs/database/` 五表一致。运行时预测与离线测试集导入分开验收。

## Requirements

### Requirement: `.pkl` 导出的特征顺序 MUST 以契约二第三节为唯一权威

expert 在线模型 MUST 序列化为 `.pkl` 落 `data_model/pipelines/expert/models/`（权重被 `.gitignore` 排除，不入库）。

**在线推理列序的权威是版本控制中的 `data_model/pipelines/expert/models/feature_order.txt`**；`docs/database/commit_feature.md` 描述落库字段，两者必须一致。交付包可以附清单副本，但副本 MUST 满足三件事：

- 明确标注副本不是仓库权威，一致性以入库的 `feature_order.txt` 为准
- 列序升版时副本 MUST 同步；不一致时停止加载或拒绝交付，不猜测顺序
- 不把压缩包中的副本作为第二套独立维护清单

> 交付包为离线安装保留副本，核验时以仓库清单及其实际加载测试为准。

#### Scenario: 后端按清单组装特征
- **WHEN** 后端加载 `.pkl` 并按特征顺序清单构造输入向量推理
- **THEN** 对同一条提交，推理结果与训练侧离线预测一致

#### Scenario: 模型文件不入库（边界场景）
- **WHEN** 全量运行后执行 `git status --short`
- **THEN** `data_model/pipelines/expert/models/` 下权重不出现（被忽略规则排除），不使用 `git add -f`

### Requirement: model_name MUST 按 <算法>_v<序号> 命名

每个模型 MUST 有形如 `<算法>_v<序号>` 的 `model_name`（如 `xgb_v1`，与契约一表三示例一致）；模型迭代 MUST 换新名字，MUST NOT 覆盖旧 `model_name` 的历史结果。

#### Scenario: 命名合法
- **WHEN** 任一模型交付
- **THEN** `model_name` 匹配 `<算法>_v<数字>` 格式，且在同批交付中唯一

#### Scenario: 名字与旧版本冲突（边界场景）
- **WHEN** 新模型沿用了已有 `model_name`（如重训后仍叫 `xgb_v1`）
- **THEN** MUST 换新序号（`xgb_v2`）；MUST NOT 覆盖旧名字 —— 覆盖会让 `prediction` 表里新旧结果混作一批，趋势看板无法解释

### Requirement: 全量预测结果文件 MUST 对应契约一表三字段

离线测试集预测产物 MUST 能按 `docs/database/prediction.md` 的 `commit_hash`、`model_name`、`risk_score`、`predicted_at`、`feature_version` 字段导入；`risk_score` 在 `[0,1]`，时间使用 UTC。`data_model/evaluation/out/data_init.sql` 是测试/演示初始化数据，不能替代 `POST /api/sync` 的实时产出。

#### Scenario: 字段逐项对齐
- **WHEN** 后端线拿离线测试集预测产物与 `docs/database/prediction.md` 逐字段比对
- **THEN** 字段名、类型、取值范围全部一致，可直接灌库

#### Scenario: 数据线不碰库（边界场景）
- **WHEN** 审查数据线脚本与依赖
- **THEN** 无数据库连接代码、无 MySQL 驱动依赖；写库逻辑仅存在于后端线

### Requirement: SHAP 依赖 MUST 随交付清单钉版本

在线 expert 权重的解释依赖及其版本 SHALL 记录于 `data_model/environment.yml`。逐模型解释与预测性能应按当前验收阈值实测；不支持解释的模型返回明确的空归因，不得伪造贡献值。

> 解释输出字段与空归因展示见 `docs/api/predict.md` 和 `docs/web_page/commit_detail.md`。

#### Scenario: 交付清单完整
- **WHEN** 后端线接收 A 方案交付
- **THEN** 清单含 `.pkl` 路径、特征顺序清单、SHAP 依赖版本；按清单安装后加载与推理可跑通

#### Scenario: 性能不达标不静默（边界场景）
- **WHEN** SHAP 实时计算使预测接口超过 500ms 分位要求
- **THEN** 实测数据登记进报告与契约变更提案，不得静默降级或换算法不通知后端线

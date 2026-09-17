## Purpose

把训练产物交付给后端线（A+C 方案）：A = `.pkl` 文件 + 特征顺序清单 + SHAP 依赖；C = 全量预测结果文件（由后端灌入 `prediction` 表）。数据线只产出文件，不碰数据库。

## ADDED Requirements

### Requirement: .pkl 导出 MUST 附特征顺序清单

模型 MUST 序列化为 `.pkl` 落 `data_model/models/`（已被 `.gitignore` 排除，不入库），且 MUST 随包交付特征顺序清单：14 项特征按契约二第三节列序（冻结版）排列，后端按此顺序组装特征向量。

#### Scenario: 后端按清单组装特征
- **WHEN** 后端加载 `.pkl` 并按特征顺序清单构造输入向量推理
- **THEN** 对同一条提交，推理结果与训练侧离线预测一致

#### Scenario: 模型文件不入库（边界场景）
- **WHEN** 全量运行后执行 `git status --short`
- **THEN** `data_model/models/` 下产物不出现（被忽略规则排除），不使用 `git add -f`

### Requirement: model_name MUST 按 <算法>_v<序号> 命名

每个模型 MUST 有形如 `<算法>_v<序号>` 的 `model_name`（如 `xgb_v1`，与契约一表三示例一致）；模型迭代 MUST 换新名字，MUST NOT 覆盖旧 `model_name` 的历史结果。

#### Scenario: 命名合法
- **WHEN** 任一模型交付
- **THEN** `model_name` 匹配 `<算法>_v<数字>` 格式，且在同批交付中唯一

#### Scenario: 名字与旧版本冲突（边界场景）
- **WHEN** 新模型沿用了已有 `model_name`（如重训后仍叫 `xgb_v1`）
- **THEN** MUST 换新序号（`xgb_v2`）；MUST NOT 覆盖旧名字 —— 覆盖会让 `prediction` 表里新旧结果混作一批，趋势看板无法解释

### Requirement: 全量预测结果文件 MUST 对应契约一表三字段

C 方案交付物 `prediction_result.csv` MUST 且仅含契约一表三字段：`commit_hash` / `model_name` / `risk_score`（0.00000–1.00000）/ `predicted_at`（UTC）/ `feature_version`。**数据线 MUST NOT 直连数据库写 `prediction` 表**，灌库责任在后端线。

#### Scenario: 字段逐项对齐
- **WHEN** 后端线拿 `prediction_result.csv` 与契约一表三逐字段比对
- **THEN** 字段名、类型、取值范围全部一致，可直接灌库

#### Scenario: 数据线不碰库（边界场景）
- **WHEN** 审查数据线脚本与依赖
- **THEN** 无数据库连接代码、无 MySQL 驱动依赖；写库逻辑仅存在于后端线

### Requirement: SHAP 依赖 MUST 随交付清单钉版本

A 方案交付 MUST 含 SHAP 依赖及其版本 pin（写入 `requirements.txt`）。SHAP 实时计算 MUST 满足后端非功能要求（95% 请求 < 500ms），无法满足时 MUST 记录实测数据并提契约变更讨论。

> 契约三「待确认」项（`explanation` 的具体算法）**已由 PR #6 结清为 SHAP**，故本 Requirement 不再含「SHAP 定稿后回填契约」这一动作 —— 那条回填已无对象。

#### Scenario: 交付清单完整
- **WHEN** 后端线接收 A 方案交付
- **THEN** 清单含 `.pkl` 路径、特征顺序清单、SHAP 依赖版本；按清单安装后加载与推理可跑通

#### Scenario: 性能不达标不静默（边界场景）
- **WHEN** SHAP 实时计算使预测接口超过 500ms 分位要求
- **THEN** 实测数据登记进报告与契约变更提案，不得静默降级或换算法不通知后端线

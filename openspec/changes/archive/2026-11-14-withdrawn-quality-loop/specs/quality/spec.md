## ADDED Requirements

### Requirement: 预测质量指标

`GET /api/quality` SHALL 以 `label_method="manual"` 的人工标签为 ground truth，与指定模型在 `prediction.risk_score` 上的二值判断（`risk_score >= threshold`）比对，返回混淆矩阵与派生指标。`model_name` 缺省时 SHALL 取表内最新模型；`threshold` 缺省时 SHALL 取当前运行时 `high_risk_threshold`。`start_time` / `end_time` 按 `commit.committed_at` 过滤，语义与 `GET /api/commits` 一致。无任何可评估样本时 SHALL 返回 `code=0` 且 `evaluated=0`、派生指标为 `null`（`MUST NOT` 用 0 冒充）。

#### Scenario: 有标签时给出混淆矩阵

- **WHEN** 2 条提交有人工标签，且各自在该模型下有 prediction（一条 0.87 标为缺陷、一条 0.21 标为非缺陷），以 `threshold=0.5` 请求
- **THEN** 返回 `code=0`，`data.evaluated=2`、`tp=1`、`tn=1`、`fp=0`、`fn=0`，`precision=1.0`、`recall=1.0`

#### Scenario: 无标签（边界）

- **WHEN** 库内没有任何 manual 标签
- **THEN** `data.evaluated=0`、`data.precision` / `recall` / `f1` / `accuracy` / `recommended_threshold` 均为 `null`，`MUST NOT` 返回 40400

#### Scenario: 标签无对应预测（边界）

- **WHEN** 某提交有人工标签，但该模型下没有 prediction 行
- **THEN** 该提交计入 `labeled_total` 但 `MUST NOT` 计入 `evaluated`（分母只算真正参与比对的行）

### Requirement: 标签回流样本导出

`GET /api/quality/dataset` SHALL 导出全部 manual 标签样本，供离线再训练使用：每项含 `commit_hash`、`is_defect`、`labeled_at`、`committed_at` 与 14 维 `features`（无特征时 `features` 为 `null`）。`MUST NOT` 触发任何预测或写入。

#### Scenario: 导出带标签样本

- **WHEN** 库内有 3 条 manual 标签，其中 2 条有 `commit_feature`
- **THEN** 返回 `count=3`，两条带完整 14 维 `features`，一条 `features=null`

### Requirement: 阈值校准

`POST /api/quality/calibrate` SHALL 用 manual 标签扫描候选阈值（0.05 ~ 0.95，步长 0.05）选出 F1 最高点，与当前运行时阈值对比；有改善时 SHALL 将 `high_risk_threshold` 写入 `runtime_setting` 并**立即生效**（无需重启），`mid_risk_threshold` SHALL 保持 `<= high_risk_threshold`。样本不足（可评估行 < 2，或标签全为正/全为负）时 SHALL 返回 `code=0` 且 `applied=false`、`reason="insufficient_labels"`，`MUST NOT` 写入任何配置。

#### Scenario: 校准并落库

- **WHEN** 标签显示当前阈值并非 F1 最优点
- **THEN** 返回 `applied=true`，`after.f1 >= before.f1`，且 `runtime_setting` 中 `high_risk_threshold` 更新为 `after.threshold`

#### Scenario: 样本不足（异常）

- **WHEN** 可评估样本少于 2 条
- **THEN** 返回 `code=0`、`applied=false`、`reason="insufficient_labels"`，`before.threshold` 仍为当前值，配置不变

### Requirement: 运行时阈值解析

`prs.get_pr_risk_level` 与 `trends` 的高风险计数 SHALL 通过 `app/services/settings.py` 读取阈值（DB 优先、`.env` 兜底），`MUST NOT` 直接读 `config.HIGH_RISK_THRESHOLD`；DB 不可用时 SHALL 静默回退 `.env` 默认值，`MUST NOT` 使请求失败。

#### Scenario: 校准后等级立即变化

- **WHEN** 校准把 `high_risk_threshold` 从 0.5 调到 0.3
- **THEN** 同一 `risk_score=0.4` 的 PR 在下一次 `GET /api/prs` 中 `risk_level` 由「低」变为「高」，无需重启进程

# 预测质量度量与标签回流闭环

## Why

`feedback-observability` 打通了「人工标记」这一环，但闭环是断的：

1. **标签没有出口**：人工确认的 `is_defect` 只静静躺在 `commit_label` 里，既不能评估模型准不准，也不能导出给离线训练用。工业级 JIT 的核心是 `预测 → 确认 → 标签回流 → 再训练/校准`，我们现在断在最后一跳。
2. **不知道模型还准不准**：没有任何 precision/recall/F1，也没有「真实缺陷 vs 非缺陷」的风险分分布对比。评审者看到的 87% 风险分，没有任何历史准确率作为背书。
3. **阈值是拍脑袋的**：`HIGH_RISK_THRESHOLD=0.5` 写死在 `.env`，与「这个模型的分数分布」无关。有了标签之后完全可以按 F1 自动选出更合适的阈值，但当前改阈值要重启。

本 change 把这三件事一次补齐：**用人工标签度量质量 → 导出回流样本 → 按标签校准阈值（落库即时生效）**。

## What Changes

- **新增 `runtime_setting` 表**（`key` / `value` / `updated_at`）：承载运行时阈值，校准结果落库、进程重启后仍生效。
- **新增 `app/services/settings.py`**：阈值读写的单一入口（DB 持久化 + 内存缓存 + 降级回退 `.env` 默认值），`MUST NOT` 各路由直接读 `config.HIGH_RISK_THRESHOLD`。
- **新增 `app/services/quality.py`**：以 manual 标签为 ground truth，与指定模型的 `prediction.risk_score` 做混淆矩阵；提供阈值扫描（0.05~0.95，步长 0.05）选 F1 最优点。
- **新增 `app/api/quality.py` 三条端点**：
  - `GET /api/quality`：质量指标（TP/FP/TN/FN、precision/recall/F1/accuracy、缺陷与非缺陷的平均风险分、推荐阈值）。
  - `GET /api/quality/dataset`：导出回流的带标签样本（含 14 维特征），供离线再训练。
  - `POST /api/quality/calibrate`：按当前标签校准 `high_risk_threshold` 并落库，返回校准前后对比。
- **阈值改为运行时解析**：`prs.get_pr_risk_level` 与 `trends` 的高风险计数改读 `services/settings.py`，校准后立即生效（无需重启）。
- **`_parse_time` 上移**到 `app/timeutil.parse_time_param`：quality 需要同样的时间参数语义，避免又出现「从路由模块 import 私有函数」。
- **前端新增「质量看板」**：指标卡 + 混淆矩阵 + 阈值校准按钮（见 change `frontend-redesign`）。

## Capabilities

### Added Capabilities

- `quality`：预测质量度量、标签回流样本导出、阈值校准。

### Modified Capabilities

- `query-api`：PR `risk_level` / 趋势 `high_risk_count` 的阈值来源改为运行时配置（默认值不变，对外字段不变）。
- `db-schema`：新增 `runtime_setting` 表（5 → 6 表）。

## Impact

- 后端：新增 `app/services/{settings,quality}.py`、`app/api/quality.py`；`app/models.py` 加 `RuntimeSetting`；`app/api/{prs,trends,commits}.py`、`app/timeutil.py`、`app/main.py`、`app/schemas.py` 调整。
- 数据库：新增 `runtime_setting` 表（无外键、无数据迁移）；`infra/schema.sql` 与 `test_schema_sql.py` 同步。
- 契约：`GET /api/quality`、`GET /api/quality/dataset`、`POST /api/quality/calibrate` 三条新路径；`test_mirror.py` 零静默扩张原则照旧。
- 测试：`conftest.py` 清空 `runtime_setting` 并重置阈值缓存，避免用例间阈值串味。

## 不做什么

- `MUST NOT` 在本 change 内做真正的模型再训练（训练是离线能力，见 `openspec/specs/model-training`）；本 change 只负责**产出回流样本 + 阈值校准**。
- `MUST NOT` 改动 `prediction` 表结构或预测口径。
- 阈值校准只调 `high_risk_threshold`（及受约束的 `mid_risk_threshold`），不改模型权重。
- 不做标签的冲突仲裁（人工 vs SZZ 谁优先）：评估只认 `label_method="manual"`。

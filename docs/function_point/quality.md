# 质量看板与阈值校准

纵向功能点：展示模型性能指标，并基于人工标签校准高风险阈值（热更新）。跨后端、前端、数据库。

## 各层职责
| 层 | 职责 |
|---|---|
| 后端 | `GET /api/quality` 指标；`POST /api/quality/calibrate` 校准；`GET /api/quality/dataset` 导出标签样本 |
| 数据库 | `runtime_setting` 存阈值；`commit_label`(manual) 供校准 |
| 前端 | 质量看板展示指标 + 触发校准 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `runtime_setting.high_risk_threshold` | 校准后阈值 |
| `commit_label`(manual) | 校准样本 |

## 验收
- 指标卡正确显示；校准后阈值即时生效于预测/门禁。

# PR 风险评估与门禁

纵向功能点：拉取 open PR、逐提交预测、给出整体风险与 CI 门禁结论。跨模型线、后端、前端。

## 各层职责
| 层 | 职责 |
|---|---|
| 模型线 | 提供预测能力 |
| 后端 | `POST /api/sync-prs` 拉取并预测；`GET /api/prs` 列表；`GET /api/prs/{n}` 详情；`GET /api/prs/{n}/gate` 门禁 |
| 前端 | PR 列表 / PR 详情页展示风险与门禁 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `prs.gate` | pass / block |
| `runtime_setting.high_risk_threshold` | 门禁判定阈值 |

## 验收
- PR 列表显示整体风险与门禁；详情页按模型展示各提交风险。

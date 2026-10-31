# 测试集评估看板

纵向功能点（本次新增）：把检验集的 commit 信息 + 14 维特征 + szz 真标签 + 各模型判断与性能图统一展示。跨模型线、数据库、后端、前端。

## 各层职责
| 层 | 职责 |
|---|---|
| 模型线 | 跑预测产出 CSV（commit 信息 + 14 维 + szz 真标签 + 各模型 risk_score）；按模型生成图集 `figs_by_model/{line}/{model}/*.png` |
| 数据库 | `commit_feature` 加 `is_test`；`model` 加 `line`；`prediction` 导入四线数据；`model_figure` 登记图元数据；真标签来自 `commit_label`(szz) |
| 后端 | `GET /api/test-detail` 明细；`GET /api/figures` + `StaticFiles` 图 |
| 前端 | eval 页：切换模型、渲染图集、浏览明细表 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `commit_feature.is_test` | 标记检验集 |
| `model.line` | 区分四方案，前端分组 |
| `prediction.risk_score` | 各模型判断 |
| `commit_label`(szz) | 真标签基准 |
| `model_figure` | 图索引 |

## 范围
- 特征仅 Kamei 14 维；语义/融合/端到端特征不落关系表；
- 判断覆盖四线 25 模型（可先 expert 8）。

## 验收
- 按 `is_test=1` 可筛出全部测试集；
- 切换任意模型，明细与图集一致对应。

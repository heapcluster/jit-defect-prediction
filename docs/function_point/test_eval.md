# 测试集评估看板

纵向功能点：把检验集（时间序后 30%）的 commit 信息、Kamei 14 维特征、szz 真标签、各模型判断与逐模型性能图统一展示。跨模型线、数据库、后端、前端。

## 各层职责
| 层 | 职责 |
|---|---|
| 模型线 | 跑预测产出 CSV（commit 信息 + 14 维 + szz 真标签 + 各模型 risk_score）；按模型生成图集 `figs_by_model/{line}/{model}/*.png` |
| 数据库 | `commit_feature` 加 `is_test`；`model` 加 `line`；`prediction` 导入四线数据；`model_figure` 登记图元数据；真标签来自 `commit_label`(szz) |
| 后端 | `GET /api/test-detail` 明细；`GET /api/figures` + `StaticFiles` 图 |
| 前端 | eval 页：切换模型、渲染逐模型图集、浏览明细表 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `commit_feature.is_test` | 标记检验集 |
| `model.line` | 区分四方案，前端分组 |
| `prediction.risk_score` | 各模型判断 |
| `commit_label`(szz) | 真标签基准 |
| `model_figure` | 图索引 |

## 范围
- 特征仅 Kamei 14 维，且仅 expert 线展示；语义 / 融合 / 端到端特征不落关系表；
- 真标签只取 szz；
- 判断覆盖四线 25 模型（可先 expert 8）；
- 图按模型产出 `roc` / `pr` / `confusion` / `calibration` / `effort`；`feat_importance` 仅 expert。

## 阈值工作点
本看板接手原质量看板的校准职责：在明细与图上选定工作点后，经 `PUT /api/config` 写入 `runtime_setting.high_risk_threshold`，立即作用于前端的风险分级与高/低判定。真值只有 szz，人工标签不参与。

## 验收
- 按 `is_test = 1` 可筛出全部测试集；
- 切换任意 `model_name`，明细与逐模型图集一致对应；
- 页面上 effort-unaware 与 effort-aware 两类指标图各至少一张（课程硬要求）；
- 未预测的提交不进明细行，用页顶「测试集 `test_total` / 已预测 `total` / 缺 K」表达缺口；MUST NOT 渲染成风险 0。

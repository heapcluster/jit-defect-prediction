# 测试集评估看板

**一句话**：把检验集（时间序后 30%）的 commit 信息、Kamei 14 维特征、szz 真标签、各模型判断与逐模型性能图**统一展示**。它支撑前端 **新增的「测试集评估」Tab 页**。

## 对应前端功能
| 页面 / 入口 | 用这个功能点的哪部分 |
|---|---|
| 顶部导航「测试集评估」Tab | 整页：线 → 模型两级切换 |
| 板块一「测试集信息 + 预测结果」 | 测试集逐条 commit + 特征（仅 expert）+ 真标签 + 选中模型分 |
| 板块二「模型效果图」 | 指标数值（auc/f1 等）+ 该模型一组性能图 |

## 各层职责
| 层 | 职责 |
|---|---|
| 模型线 | 跑预测产出 CSV（commit 信息 + 14 维 + szz 真标签 + 各模型 risk_score）；按模型生成图集 `figs_by_model/{line}/{model}/*.png` |
| 数据库 | `commit_feature` 加 `is_test` + `is_bug_inducing`（真标签并入）；`model` 加 `line`；`prediction` 导入四线数据；`model_figure` 登记图元数据 |
| 后端 | `GET /api/models` 模型清单（两级选择器数据源）；`GET /api/test-detail` 明细；`GET /api/figures`（图 + `metrics` 指标） + `StaticFiles` 图 |
| 前端 | eval 页：线 → 模型两级切换、渲染指标数值 + 逐模型图集、浏览明细表 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `commit_feature.is_test` | 标记检验集 |
| `commit_feature.is_bug_inducing` | szz 真标签基准（原 `commit_label` 并入） |
| `model.line` | 区分四方案，前端分组 |
| `prediction.risk_score` | 各模型判断 |
| `model_figure` | 图索引 |

## 范围
- 特征仅 Kamei 14 维，且仅 expert 线展示；语义 / 融合 / 端到端特征不落关系表；
- 真标签只取 szz（`commit_feature.is_bug_inducing`）；
- 判断覆盖四线 25 模型（可先 expert 8）；
- 图按模型产出 `roc` / `pr` / `confusion` / `calibration` / `effort`；`feat_importance` 仅 expert。

## 阈值工作点
阈值**写死 `.env`（`HIGH_RISK_THRESHOLD` / `MID_RISK_THRESHOLD`）**，`runtime_setting` 表已删除，`PUT /api/config` 热更新已下线。看板只展示指标与图，不再承担校准写库职责；真值只有 szz，人工标签不参与。

## 验收
- 按 `is_test = 1` 可筛出全部测试集；
- 模型清单来自 `GET /api/models`（按 line 分组），前端不写死；
- 切换任意 `line` → `model_name`，明细、指标数值（auc/f1 等）与逐模型图集一致对应；
- 页面上 effort-unaware 与 effort-aware 两类指标图各至少一张（课程硬要求）；
- 未预测的提交不进明细行，用页顶「测试集 N / 已预测 M / 缺 K」表达缺口；MUST NOT 渲染成风险 0。

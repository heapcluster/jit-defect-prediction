# 模型性能看板

**一句话**：新「模型性能」页的能力——选定模型查看测试集性能评估图/指标，并在同一页按提交查看 Kamei 14 维、SZZ 真标签与所选模型的缺陷引入概率。

## 对应前端功能
| 页面 / 入口 | 用这个功能点的哪部分 |
|---|---|
| 顶部导航「模型性能」（`/model-performance`） | 整页 |
| 架构 → 模型（两级级联）+ 时间范围（独立） | 选架构（`line`）→ 选该架构下的模型；时间范围可单独选择；未选模型 = 默认模型 |
| 「查看」抽屉 | 该模型的性能评估图集（`roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance`），指标数值可一并展示 |
| 多维指标表格（仅测试集） | `is_test=1` + `with_features=1`：测试集提交 + 14 维特征 + SZZ 判断 + 所选模型概率；支持搜索、时间范围、分页 |

## 各层职责
| 层 | 职责 |
|---|---|
| 模型线 | 时间序切分测试集（后 30%）、SZZ 打标、逐模型评估，产出图集与指标；把 `is_test` / `is_bug_inducing` / `labeled_at` 写入 `commit_feature`、预测写入 `prediction` |
| 数据库 | `model.line` 分组；`commit_feature`（14 维 + `is_test` + 真标签）；`prediction`（各模型概率）；`model_figure`（图索引） |
| 后端 | `GET /api/models` 级联数据；`GET /api/figures?model_name=` 图 + 指标；`GET /api/commits?with_features=1&is_test=1` 多维表格；`StaticFiles` 托管图 |
| 前端 | 架构 → 模型两级级联 + 独立时间范围；「查看」抽屉（带 `X-API-Key` fetch 图片转 `ObjectURL`）；多维表格与分页 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `model.line` | 架构分组（`expert` / `semantic` / `fused` / `e2e`，小写） |
| `commit_feature.is_test` | 性能图、指标与表格的数据范围（时间序后 30% 测试集） |
| `commit_feature.is_bug_inducing` | SZZ 真标签；库内外同名（`1` / `0` / `null`） |
| `commit_feature` 14 维 | 表格特征列；log 变换值，可负 |
| `prediction.risk_score` | 所选模型对每条提交的概率，随模型切换整列刷新 |
| `model_figure` | 逐模型图索引与静态路径 |

## 范围与口径
- **图、指标与表格统一为测试集口径**：性能图与指标在 `is_test = 1` 上计算；下方表格固定 `is_test=1`，展示全部测试集提交的逐条结果，不混入训练集。
- **14 维只展示 Kamei 14 维**，且是 log 变换值；语义 768 维、融合 782 维、e2e 文本不落关系表。需要可读原值时由前端做 `exp` 还原，契约层不还原。
- **真标签只取 SZZ**（`commit_feature`）；人工标签已下线。未打标提交返回 `null`，页面显示「无 SZZ 标记」，MUST NOT 当成非缺陷。
- 表格只包含**测试集内已预测**的提交（`is_test=1` 且 `prediction` 与 `commit` 内连接）；未预测的测试集提交表现为缺行，不能渲染成风险 0。
- 模型清单来自 `GET /api/models`，前端 MUST NOT 写死；架构中文名由后端返回，前端可兜底。
- 阈值（高/中风险）写死 `.env`（`HIGH_RISK_THRESHOLD` / `MID_RISK_THRESHOLD`），`runtime_setting` 已删除。

## 数据准备（联调前）
1. 在 `data_model/` 执行 `python -m evaluation.run_all`，生成：
   - `evaluation/out/schema.sql`：建表 DDL
   - `evaluation/out/data_init.sql`：`commit`（测试集）/ `commit_feature`（14 维 + `is_test` + `is_bug_inducing` + `labeled_at`）/ `model`（25 个）/ `prediction`（25 模型 × 测试集）/ `model_figure`
   - `evaluation/out/model_metrics.csv`：25 模型聚合指标
2. 依次导入 MySQL：`schema.sql` → `data_init.sql`。
3. 接口分工：
   - 逐条表格：`GET /api/commits?with_features=1&is_test=1` 读 MySQL，不读 `out/`，不在请求时跑脚本。
   - 图 + 指标：`GET /api/figures?model_name=` 读 `model_figure` 与 `out/model_metrics.csv`。
## 验收
- 切换架构 / 模型或时间范围：表格概率列与「查看」抽屉图集同步刷新；模型不选时走后端默认模型。
- 表格列齐全：提交、作者、时间、提交信息、14 维特征、SZZ 判断（`is_bug_inducing`）、缺陷引入概率（`risk_score`）；`with_features=1&is_test=1` 才能拿到测试集特征列。
- SZZ 三态正确：有标签 `1` / `0`，未打标 `null`；不得把 `null` 显示成「非缺陷」。
- 图集覆盖 `roc` / `pr` / `confusion` / `calibration` / `effort`，expert 架构另有 `feat_importance`；effort-unaware 与 effort-aware 两类指标图各至少一张（课程硬要求）。
- 图片请求带鉴权头；`<img>` 直连静态路径不算通过。
- 指标数值与图对应同一模型；切换模型后不得残留上一个模型的图或指标。

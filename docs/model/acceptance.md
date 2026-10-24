# 模型验收功能板块（达到什么效果）

> 验收人：sober / 苏哲勋 ｜ Sprint：Sprint 0（链路）→ Sprint 1（8 模型/两类指标）→ Sprint 3（校准证据）

## 板块 M1：数据可复现

- **效果**：固定在 `camel-4.23.0`（`b2329103…`），别人照命令跑出 84,461 条、正负样本与比例（±0）。
- **证据**：复现命令输出 + `reports/` 统计表。一票否决：版本浮动 `main`。

## 板块 M2：SZZ 打标

- **效果**：标准行级 + 文件级简化版两套均跑，差异量化出示；判据 D4 为 `CAMEL-编号` 且修复词首边界；当前外沿登记见 `data-pipeline.md` §7（不复用旧仓库假阳性统计）。
- **证据**：`szz_labeling_stats.md`。

## 板块 M3：Kamei 14 项特征

- **效果**：14 项特征口径一致（`feature-columns.md`），`features` 键名与接口/前端同源。
- **证据**：`feature_stats.md` + 键名核对。一票否决：三处键名不一致。

## 板块 M4：8 种模型 / 2 类

- **效果**：经典 6 + 深度学习 2，总量不减（分期后置）；两类指标齐全。
- **证据**：`model_matrix.md`（8×2×两类，与训练报告差异 0）。一票否决：只报一类指标。

## 板块 M5：时间序切分

- **效果**：前 70%/后 30% 时间序，禁随机；`--selfcheck` 拦住打乱输入。
- **证据**：切分报告 + selfcheck 通过。

## 板块 M6：全量预测交付

- **效果**：`prediction_result.csv` 字段=契约一表三，不夹带契约外字段；全量含检验集。
- **证据**：交付文件 + 字段核对。

## 板块 M7：解释（SHAP）

- **效果**：`explanation[]` 逐特征带 direction，实时与查询接口同结构。
- **证据**：接口返回示例 + 前端联调。

## 板块 M8：校准与阈值证据

- **效果**：时间序折校准 + 固定阈值/工作量配额对照（Sprint 3 非功能相关）。
- **证据**：`calibration_threshold.md`。

## 三端联调 · 模型线要求（2026-10-23 定稿）

**目标**：后端加载的权重、前端展示的分数，都能追溯到同一次训练、同一份切分。

1. **权威指标由重训产出**：`model_metrics.md` 必须来自在当前 `split_szz_*.csv` 上的重新训练（58,760 / 25,183）；`--from-saved` 只写 `model_metrics_from_saved.md` 并标注「探索性」。
2. **权重可被后端干净进程加载**：`tabnet_v1.pkl` 依赖 `pipelines.expert.model.TabNetWithEarlyStop`，后端需把 `data_model` 加入 `sys.path` 并安装 `torch` / `pytorch_tabnet`；其余 7 个为 sklearn 对象，无额外依赖。
3. **特征映射书面化**：给出 `commit_features.csv` 列名 → 契约 14 列（`ns,nd,nf,entropy,la,ld,lt,fix,ndev,age,nuc,exp,rexp,sexp`）的对照，注明 `fix` 入库为 int、其余 float。
4. **全量预测结果**：`prediction_result.csv` 字段 = 契约一表三（`commit_hash / risk_score / model_name / predicted_at / feature_version`），`model_name` 与 pkl 名一致（`xgb_v1` 形式），可直接被 `app.ingest predictions` 消费。
5. **SHAP 口径要说实话**：树模型与线性模型为实测耗时；`svm` / `mlp_deep` / `tabnet` 无精确 Tree/Linear 解释器，报告中写「无精确 SHAP 解释器」，不得写「已实现」。
6. **证据**：`reports/model_metrics.md` + `reports/figs/` 三张图 + `data_model/tests` 全量通过（当前 105 条）。

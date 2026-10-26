# 四线并排对照表（同切分、同指标口径）

> **数字来源**：各线 `data_model/pipelines/<line>/reports/model_metrics.md` 原文，按字符串搬运，本表不重算、不重格式化。生成脚本 `build_comparison.py`（离线只读）。
> **共同口径**：切分 `data/split_szz_{train,test}.csv`；检验集 **25,183** 条、正样本比例 **14.38%**；判定阈值 0.5；随机种子 42；effort-aware 的工作量代理 = LOC（`la+ld`）。
> **四条线的唯一变量是特征模态**：
> - `expert` = Kamei 14 维（契约二第三节顺序）
> - `semantic` = 冻结 CodeBERT 768 维（mean-pool）
> - `fused` = Kamei 14 ⊕ 冻结语义 768 = 782 维
> - `e2e` = CodeBERT 端到端微调（唯一做反向传播的一条）

## 〇、摘要（每线一行，最好 AUC 的那个模型）

| 线 | 特征模态 | 最好 AUC（模型） | 最好 P_norm（模型） | 在线可上线 |
|---|---|---|---|---|
| `expert` | Kamei 14 维（契约二第三节顺序） | **0.8294**（tabnet_v1） | **-0.0791**（svm_v1） | ✅ 是，**8 个全部可上线切换**（#153 起；后端 `FEATURE_COLUMNS` 实测 14 列，`model_registry.py:104-112` 对特征数 ≠ 14 的权重打 `model skipped` 并计入 `failed`） |
| `semantic` | 冻结 CodeBERT 768 维（mean-pool） | **0.7644**（mlp_deep_semantic_v1） | **0.3526**（xgb_semantic_v1） | ❌ 否（768 维，加载期即被拒收） |
| `fused` | Kamei 14 ⊕ 冻结语义 768 = 782 维 | **0.8395**（lgbm_fused_v1） | **0.2549**（mlp_deep_fused_v1） | ❌ 否（782 维，加载期即被拒收） |
| `e2e` | CodeBERT 端到端微调（唯一做反向传播的一条） | **0.7553**（codebert_e2e_v1） | **-0.1995**（codebert_e2e_v1） | ❌ 否（端到端，无 14 维特征接口） |

## 一、Effort-unaware（检验集）

| 线 | 模型 | AUC | F1 | Precision | Recall | Accuracy |
|---|---|---|---|---|---|---|
| `expert` | `tabnet_v1`（TabNet（深度表格）） | 0.8294 | 0.4437 | 0.4617 | 0.4271 | 0.8460 |
| `expert` | `xgb_v1`（XGBoost） | 0.8281 | 0.4316 | 0.4587 | 0.4075 | 0.8456 |
| `expert` | `lgbm_v1`（LightGBM） | 0.8260 | 0.4337 | 0.4510 | 0.4177 | 0.8431 |
| `expert` | `mlp_deep_v1`（多层感知机（3 隐藏层 + 早停）） | 0.8254 | 0.4084 | 0.5116 | 0.3399 | 0.8584 |
| `expert` | `et_v1`（极端随机树（Extra Trees）） | 0.8223 | 0.3955 | 0.5212 | 0.3186 | 0.8599 |
| `expert` | `rf_v1`（随机森林） | 0.8190 | 0.4083 | 0.5215 | 0.3355 | 0.8601 |
| `expert` | `lr_v1`（逻辑回归） | 0.8020 | 0.3497 | 0.5303 | 0.2609 | 0.8605 |
| `expert` | `svm_v1`（RBF 核支持向量机） | 0.7096 | 0.4078 | 0.5464 | 0.3252 | 0.8641 |
| `semantic` | `mlp_deep_semantic_v1`（多层感知机（3 隐藏层 + 早停）） | 0.7644 | 0.1879 | 0.3677 | 0.1262 | 0.8431 |
| `semantic` | `tabnet_semantic_v1`（TabNet（深度表格）） | 0.7631 | 0.2041 | 0.3387 | 0.1461 | 0.8362 |
| `semantic` | `lgbm_semantic_v1`（LightGBM） | 0.7615 | 0.1566 | 0.3084 | 0.1049 | 0.8374 |
| `semantic` | `xgb_semantic_v1`（XGBoost） | 0.7605 | 0.1683 | 0.3212 | 0.1140 | 0.8379 |
| `semantic` | `et_semantic_v1`（极端随机树（Extra Trees）） | 0.7564 | 0.0726 | 0.4150 | 0.0398 | 0.8538 |
| `semantic` | `lr_semantic_v1`（逻辑回归） | 0.7551 | 0.1449 | 0.2798 | 0.0977 | 0.8341 |
| `semantic` | `rf_semantic_v1`（随机森林） | 0.7522 | 0.0694 | 0.3629 | 0.0384 | 0.8520 |
| `semantic` | `svm_semantic_v1`（RBF 核支持向量机） | 0.6538 | 0.1521 | 0.3538 | 0.0969 | 0.8447 |
| `fused` | `lgbm_fused_v1`（LightGBM） | 0.8395 | 0.4316 | 0.4962 | 0.3818 | 0.8553 |
| `fused` | `xgb_fused_v1`（XGBoost） | 0.8342 | 0.4187 | 0.4895 | 0.3658 | 0.8539 |
| `fused` | `tabnet_fused_v1`（TabNet（深度表格）） | 0.8277 | 0.4120 | 0.4738 | 0.3644 | 0.8504 |
| `fused` | `rf_fused_v1`（随机森林） | 0.8155 | 0.2136 | 0.5557 | 0.1322 | 0.8600 |
| `fused` | `lr_fused_v1`（逻辑回归） | 0.8134 | 0.3508 | 0.4586 | 0.2841 | 0.8488 |
| `fused` | `et_fused_v1`（极端随机树（Extra Trees）） | 0.8098 | 0.1427 | 0.5155 | 0.0828 | 0.8569 |
| `fused` | `mlp_deep_fused_v1`（多层感知机（3 隐藏层 + 早停）） | 0.8053 | 0.3641 | 0.4438 | 0.3087 | 0.8449 |
| `fused` | `svm_fused_v1`（RBF 核支持向量机） | 0.7540 | 0.3531 | 0.4796 | 0.2794 | 0.8528 |
| `e2e` | `codebert_e2e_v1` | 0.7553 | 0.1125 | 0.3155 | 0.0685 | 0.8447 |

## 二、Effort-aware（LOC 工作量代理；「模型排序」= 契约三当前口径 `risk_score` 降序）

| 线 | 模型 | 曲线下面积 | **P_norm** | Recall@20% | Recall@50% |
|---|---|---|---|---|---|
| `expert` | `lr_v1` | 0.3186 | **-0.3814** | 0.0458 | 0.3545 |
| `expert` | `rf_v1` | 0.4070 | **-0.1955** | 0.1789 | 0.3940 |
| `expert` | `xgb_v1` | 0.3632 | **-0.2876** | 0.1207 | 0.3418 |
| `expert` | `lgbm_v1` | 0.3375 | **-0.3416** | 0.1452 | 0.2686 |
| `expert` | `et_v1` | 0.4539 | **-0.0970** | 0.1742 | 0.5284 |
| `expert` | `svm_v1` | 0.4624 | **-0.0791** | 0.1632 | 0.5235 |
| `expert` | `mlp_deep_v1` | 0.4063 | **-0.1970** | 0.1579 | 0.3832 |
| `expert` | `tabnet_v1` | 0.3846 | **-0.2428** | 0.1618 | 0.3675 |
| `semantic` | `lr_semantic_v1` | 0.6582 | **0.3325** | 0.3879 | 0.7465 |
| `semantic` | `rf_semantic_v1` | 0.4995 | **-0.0010** | 0.3001 | 0.4660 |
| `semantic` | `xgb_semantic_v1` | 0.6678 | **0.3526** | 0.4136 | 0.7714 |
| `semantic` | `lgbm_semantic_v1` | 0.6575 | **0.3311** | 0.4042 | 0.7783 |
| `semantic` | `et_semantic_v1` | 0.6166 | **0.2451** | 0.4039 | 0.6806 |
| `semantic` | `svm_semantic_v1` | 0.5232 | **0.0487** | 0.3655 | 0.5066 |
| `semantic` | `mlp_deep_semantic_v1` | 0.6157 | **0.2431** | 0.3542 | 0.7087 |
| `semantic` | `tabnet_semantic_v1` | 0.6415 | **0.2974** | 0.3893 | 0.7427 |
| `fused` | `lr_fused_v1` | 0.5175 | **0.0367** | 0.1314 | 0.6182 |
| `fused` | `rf_fused_v1` | 0.5321 | **0.0675** | 0.2408 | 0.6273 |
| `fused` | `xgb_fused_v1` | 0.5506 | **0.1063** | 0.1817 | 0.6676 |
| `fused` | `lgbm_fused_v1` | 0.5034 | **0.0071** | 0.1541 | 0.5602 |
| `fused` | `et_fused_v1` | 0.5924 | **0.1941** | 0.2504 | 0.7327 |
| `fused` | `svm_fused_v1` | 0.5098 | **0.0206** | 0.1974 | 0.6113 |
| `fused` | `mlp_deep_fused_v1` | 0.6213 | **0.2549** | 0.1593 | 0.7515 |
| `fused` | `tabnet_fused_v1` | 0.4248 | **-0.1581** | 0.1869 | 0.4119 |
| `e2e` | `codebert_e2e_v1` | 0.4051 | **-0.1995** | 0.2057 | 0.3915 |

**四线共用的参照行**（各线报告原文一致）：

| 参照 | 曲线下面积 | P_norm | Recall@20% | Recall@50% |
|---|---|---|---|---|
| 上界：真实缺陷密度降序 | 0.9757 | 1.0000 | 0.9903 | 1.0000 |
| 基线：随机排序（200 次均值） | 0.5000 ± 0.0166 | 0.0000 | — | — |

> 各线还有一行「对照」排序（`expert` 报告无此行；`e2e` = 按 `risk_score / 工作量` 降序 0.9282 / 0.9001；`semantic`/`fused` = 密度排序，逐模型见各自报告），本表不并入，避免与「模型排序」口径混淆。

## 三、按两份报告里写好的判据读（可直接抄进「对照读法」两段）

1. **融合对照读法**（`fused` 报告 §「融合对照读法」的判据：fused 优于两者 = 两模态互补；只与 expert 持平 = 语义无增量）：fused 最好 AUC **0.8395**（lgbm_fused_v1）> expert 最好 **0.8294**（tabnet_v1），差 **+0.0101** → **两模态互补**，不是持平。
2. **与 baseline 对照**（`semantic` 报告 §「与 baseline 对照（读法）」的判据：不升反降要如实登记）：semantic 最好 AUC **0.7644**（mlp_deep_semantic_v1）< expert **0.8294**，差 **-0.0650** → **纯语义模态单独用无增量**，如实登记。
3. **e2e**：AUC **0.7553** < expert **0.8294** → 端到端微调（报告自证 `epochs=1`，冒烟轮次，不冒充满轮）未超过 Kamei14 手工特征。
4. **effort-aware 与 effort-unaware 排序反向**（建议登记进 #37 的补充证据，本次不改现状）：`expert` P_norm 为负 **8/8** 个（最好 svm_v1 -0.0791）；`semantic` P_norm 为负 **1/8** 个（最好 xgb_semantic_v1 0.3526）；`fused` P_norm 为负 **1/8** 个（最好 mlp_deep_fused_v1 0.2549）；`e2e` P_norm 为负 **1/1** 个（最好 codebert_e2e_v1 -0.1995）。→ 语义模态把 effort-aware 从「全负」救回「多为正」，但同时把 AUC 拉低；融合把 AUC 救回来、P_norm 又掉到 semantic 之下。**两列不存在同一条线同时最优**，所以「主线选哪条」必须先定用哪一列当判据。
5. **口径结论（蒋励 2026-10-25 裁定）**：在线交付主线 = `expert`，其余三条走离线对照；排序维持 `risk_score` 降序，MVP 内不改（改它要动契约三，#37 已按里程碑冻结）。
   理由经后端侧实测复核成立（引用行号已核到 main `1b0cf6d`）：`backend/app/config.py:23-28` 的 `FEATURE_COLUMNS` 实测 `len = 14`（`ns/nd/nf/entropy/la/ld/lt/fix/ndev/age/nuc/exp/rexp/sexp`）；`backend/app/model_registry.py:104-112` 在 `_feature_count(model) != len(config.FEATURE_COLUMNS)` 时打 `model skipped: expects %s features, contract has %s` 并把该权重计入 `failed`（加载期就拒收，Issue #46） → 768 / 782 / 端到端三条都进不了在线清单。
6. **在线清单口径在 2026-10-25 17:16 变过一次（#153，main `9ae654c`，Issue #139 组长裁定）**：`data_model/pipelines/expert/models/feature_order.txt` 的 `[models]` 段已从 **3 个**（`lr_v1`/`rf_v1`/`xgb_v1`）扩到 **expert 全部 8 个**（+`lgbm_v1`/`et_v1`/`svm_v1`/`mlp_deep_v1`/`tabnet_v1`），同时改了 `backend/app/model_registry.py`、`backend/tests/test_model_registry.py`（+44 行）、`data_model/tests/test_feature_contract.py`、`frontend/src/utils/models.js`，并新增证据 `backend/scripts/evidence/online-eight-model-selection-2026-10-25.md`。所以上面「在线可上线」一列的准确含义是：**expert 的 8 个权重现在全部可上线切换**（不再是 3 个）。**连带影响（后端侧我认领）**：我 10-25 15:3x 在演示库上实测的启动日志 `loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']`、已合入的 T-ST 记录（#152）里「清单外 5 个模型 → `40001`」的判据、以及 `demo_preflight.py` 的 `--expect-models` 默认值 `lr_v1,rf_v1,xgb_v1`，**都是 #153 之前的口径**，需在 main 上复跑并出补记；在复跑之前，那 5 个模型走 `POST /api/predict` 应当返回 **200** 而不是 40001。


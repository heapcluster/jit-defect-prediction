# 权重交付校验证据（expert 线）

> 生成：2026-10-24T03:38:29Z ｜ 脚本：`python -m pipelines.verify_all_weights --report`（离线，不进后端运行时）
> 环境：python 3.12.14 / sklearn 1.9.1 / xgboost 3.4.1 / lightgbm 4.6.0 / torch 2.14.1+cpu
> 结论：**8/8 可加载**；无问题 ｜ 期望特征宽度 14

## 口径

- 本表只证明「**评估可用**」：8 个权重都能被干净进程回读、指标可复算。
- **不等于在线可切换**：在线加载清单仍由 `feature_order.txt` 的 `[models]` 段声明（`specs/model-coverage` R6），本脚本不改交付边界。
- 交付与验收**以 md5 匹配的那份为准**；md5 不同即另一版导出，须先核对类路径与指标。

## 逐权重

| 文件 | md5 | 大小 | 顶层类 | 内层估计器 | 特征宽度 | 加载 |
|---|---|---|---|---|---|---|
| `et_v1.pkl` | `159f751f22bcad2ff11d53646e5cbc28` | 546.4MB | `sklearn.ensemble._forest.ExtraTreesClassifier` | — | 14 | ✅ |
| `lgbm_v1.pkl` | `5b34ddfb98cfc628cd17f1a2f4cf068e` | 1.0MB | `lightgbm.sklearn.LGBMClassifier` | — | 14 | ✅ |
| `lr_v1.pkl` | `28c65f8c3d653af53af71fac350f42fe` | 0.0MB | `sklearn.pipeline.Pipeline` | `sklearn.preprocessing._data.StandardScaler`<br>`sklearn.linear_model._logistic.LogisticRegression` | 14 | ✅ |
| `mlp_deep_v1.pkl` | `97447d2f1874e579410e8f23489e629d` | 0.1MB | `sklearn.pipeline.Pipeline` | `sklearn.preprocessing._data.StandardScaler`<br>`sklearn.neural_network._multilayer_perceptron.MLPClassifier` | 14 | ✅ |
| `rf_v1.pkl` | `1960cd98722f250fd56293f998e1bdee` | 279.4MB | `sklearn.ensemble._forest.RandomForestClassifier` | — | 14 | ✅ |
| `svm_v1.pkl` | `be0a7d26c72faabbd371c83710d84550` | 3.2MB | `sklearn.pipeline.Pipeline` | `sklearn.preprocessing._data.StandardScaler`<br>`sklearn.svm._classes.SVC` | 14 | ✅ |
| `tabnet_v1.pkl` | `201a002b78c61a9589bec9b14496533c` | 0.3MB | `sklearn.pipeline.Pipeline` | `sklearn.preprocessing._data.StandardScaler`<br>`pipelines.expert.model.TabNetWithEarlyStop` | 14 | ✅ |
| `xgb_v1.pkl` | `56138e2b4b55fbcae83aaa2866d244de` | 1.2MB | `xgboost.sklearn.XGBClassifier` | — | 14 | ✅ |

## 复现命令

```bash
cd data_model
python -m pipelines.verify_all_weights --check
```

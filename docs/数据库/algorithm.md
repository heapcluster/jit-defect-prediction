# algorithm

## 用途

本项目固定的算法清单。系统启动时按本文幂等写入，训练页只按模型线读取；不依赖外部注册表，也不允许运行时新增或修改。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `line` | VARCHAR(16) | 否 | — | `expert` / `semantic` |
| `algo` | VARCHAR(64) | 否 | — | 算法标识 |
| `family` | VARCHAR(32) | 否 | — | 算法类别，取值见 `约束/enums.md` |
| `hyperparams_json` | TEXT | 否 | — | 超参数 schema 与默认值 |
| `enabled` | TINYINT(1) | 否 | 1 | 是否可训练；本文清单全部为 1 |
| `description` | VARCHAR(255) | 是 | NULL | 说明 |

## 固定清单

两条模型线各注册同一份 13 个算法，共 26 行，全部 `enabled=1`，由用户自行勾选。

| algo | family | 名称 | 超参与默认值 |
|---|---|---|---|
| `lr` | `linear` | 逻辑回归 | `C=1.0`、`max_iter=1000` |
| `dt` | `tree` | 决策树 | `max_depth=10`、`min_samples_split=2` |
| `rf` | `ensemble` | 随机森林 | `n_estimators=200`、`max_depth=20` |
| `et` | `ensemble` | 极端随机树 | `n_estimators=200`、`max_depth=20` |
| `ada` | `boosting` | AdaBoost | `n_estimators=100`、`learning_rate=0.1` |
| `gbdt` | `boosting` | 梯度提升树 | `n_estimators=200`、`learning_rate=0.1`、`max_depth=3` |
| `xgb` | `boosting` | XGBoost | `n_estimators=300`、`learning_rate=0.1`、`max_depth=6` |
| `lgbm` | `boosting` | LightGBM | `n_estimators=300`、`learning_rate=0.1`、`num_leaves=31` |
| `svm` | `svm` | 支持向量机 | `C=1.0`、`kernel=rbf`、`gamma=scale` |
| `knn` | `neighbor` | K 近邻 | `n_neighbors=5`、`weights=uniform` |
| `mlp` | `neural` | 多层感知机 | `hidden_layers=[128,64]`、`alpha=0.0001`、`max_iter=1000` |
| `dnn` | `neural` | 深度神经网络 | `hidden_layers=[256,128]`、`dropout=0.2`、`epochs=50`、`batch_size=256`、`learning_rate=0.001` |
| `tabnet` | `neural` | TabNet | `n_d=16`、`n_a=16`、`epochs=50`、`batch_size=256` |

- `svm.kernel` 取值 `linear` / `rbf` / `poly`；`knn.weights` 取值 `uniform` / `distance`。
- `hidden_layers` 为整数数组；语义线同样使用这套默认值。
- 超参只在训练页基础配置中展示，不提供搜索与自动调优。

## 产物格式

| 算法 | `framework` | `format` | 说明 |
|---|---|---|---|
| `lr` / `dt` / `rf` / `et` / `ada` / `gbdt` / `xgb` / `lgbm` / `svm` / `knn` / `mlp` | `sklearn` | `pkl` | joblib 保存完整 Pipeline |
| `dnn` / `tabnet` | `pytorch` | `pt` | 单文件 `.pt`，内含 `state_dict`、算法、超参、特征顺序与预处理 Pipeline，格式标记 `jit-pt-v1` |

- 两线格式一致，产物格式由 `algo` 决定，训练页与预测页不得自行改扩展名。

## 约束与索引

- 主键 `(line, algo)`。
- 本文是算法清单、数量与超参的唯一真源；代码内常量必须与本文一致，新增或删除算法先改本文。
- 启动时按 `(line, algo)` 幂等写入：不存在则插入；已存在时仅当超参与本文不一致才更新 `hyperparams_json`，其余字段不覆盖。
- 两线合计固定 26 行。

## 读写方

- 写入：系统启动种子。
- 读取：`GET /api/algorithms`、数据存储页算法库、训练页算法选择。
- 页面不提供新增、编辑、停用入口。

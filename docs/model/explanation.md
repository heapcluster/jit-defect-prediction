# 缺陷归因 / 解释（SHAP）

> 负责人：蒋励 ｜ 关联：契约三「冻结结论」`explanation` 算法 = SHAP
> 课程模块：「预测与解释模块（缺陷概率、缺陷归因/解释）」。

## 1. 为什么是 SHAP

契约三要求 `explanation` 逐特征且带 `direction`（推高/降低）。SHAP 天然满足；全局特征重要性无方向、非逐样本，满足不了。

- 树模型：`TreeExplainer`（xgb/rf/dt）。
- 数据与模型线需在 `data_model/environment.yml` 加 `shap` 依赖。

## 2. 接口返回结构

```json
"explanation": [
  { "feature": "entropy", "contribution": 0.21, "direction": "increase" },
  { "feature": "nuc",    "contribution": 0.14, "direction": "increase" },
  { "feature": "exp",    "contribution": 0.09, "direction": "decrease" }
]
```

- 与 `GET /api/commits/{hash}` 第 2 节、`POST /api/predict` 第 4 节**同一套结构，两处不许各写一份**。
- 前端只说「推高/降低」，不解释数值含义；换解释算法不影响页面结构。

## 3. 页面展示约定（前端侧）

- 每条读作「这个特征把风险推高/降低了多少」：`increase` 右、`decrease` 左。
- 按 `|contribution|` 降序，页面只显前 8；多出的折叠。
- `features` 键名必须与 `feature-columns.md` 一致，否则解释条取不到值、静默空白。

## 4. 验收

- 解释模块对实时推理与查询接口都产出 `explanation[]` 且带 direction。
- 前端解释条与 `explanation` 字段对应正确（联调核对）。

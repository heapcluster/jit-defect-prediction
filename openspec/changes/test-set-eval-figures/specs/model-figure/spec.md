## ADDED Requirements

### Requirement: 模型效果图类型包含 effort

`model_figure.figure_type` SHALL 支持 `roc`、`pr`、`confusion`、`calibration`、`effort`、`feat_importance` 六种取值。`effort` 表示 effort-aware 曲线：按 `risk_score` 降序累计工作量（LOC 代理 `la + ld`）与召回率，并给出随机基线与 oracle 上界作对照。特征重要性 `feat_importance` 仅对 `expert` 线（Kamei 14 维可读）产出；语义/融合 768 维与端到端文本不产出该图。

#### Scenario: 图集包含 effort

- **WHEN** 前端按 `model_name` 请求 `GET /api/figures`
- **THEN** 返回的 `figures[].figure_type` 可包含 `effort`，且 `file_path` 指向 `/static/figures/{line}/{model}/effort.png`

#### Scenario: 缺某类图时不阻塞

- **WHEN** 某模型未生成某一类图（如非 expert 线没有 `feat_importance`）
- **THEN** `GET /api/figures` 不因缺少该类型报错，只返回 `model_figure` 中已登记的行

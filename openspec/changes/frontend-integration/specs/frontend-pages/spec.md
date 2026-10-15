## ADDED Requirements

### Requirement: 三个页面与字段契约一致

前端 SHALL 提供三个页面：风险列表、提交详情、缺陷引入趋势看板；所有页面字段名 MUST 与契约 `docs/backend/api-spec.md` 逐字一致，前端 MUST NOT 改名字段；所有请求 MUST 携带 `X-API-Key`。

#### Scenario: 风险列表查询与筛选

- **WHEN** 用户在风险列表按 `model_name` / `min_risk` / 时间范围筛选并翻页
- **THEN** 列表按 `risk_score` 降序返回，字段取自 `docs/frontend/pages.md` §2（含 `items[].risk_score` 等），前端不重算排序口径

#### Scenario: 提交详情展示风险与解释

- **WHEN** 用户从风险列表点击某条提交进入详情
- **THEN** 详情展示风险值、模型版本、SHAP 解释条（`explanation[].feature/contribution/direction`，按 `|contribution|` 降序取前 8）与 14 项特征值的五维度分组

#### Scenario: 趋势看板聚合

- **WHEN** 用户在趋势看板选择 `granularity`（`week`/`month`）与 `model_name`
- **THEN** 折线取 `series[].avg_risk`，汇总项为提交总数求和与平均风险按 `commit_count` 加权；数据点 < 2 时不画折线，只显明细表并提示「数据点不足」

### Requirement: 统一三态与错误码处理

三个页面 SHALL 统一处理加载中、空数据、错误三种状态；空数据 MUST NOT 当作错误展示；错误码处理 MUST 与契约三一致（`40100` 令牌失效、`40001` 参数非法、`40400` 提交不存在、`50000` 服务异常）。

#### Scenario: 错误码分发

- **WHEN** 任一接口返回非 `0` 的 `code`
- **THEN** 页面按错误码进入对应三态：`40100` 给重新登录提示、`40400` 提示「该提交不存在」、`50000` 提示「服务异常」且不暴露堆栈或 SQL；`explanation` 为空数组时显示「该模型未提供特征解释」并保留特征值区域

#### Scenario: 风险着色阈值一处定义

- **WHEN** 页面渲染风险等级标签或着色
- **THEN** 阈值口径只用后端常量（`≥0.5` 高 / `≥0.3` 中 / 其余常规），前端不另行定义第二份阈值

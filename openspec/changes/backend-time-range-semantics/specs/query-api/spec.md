## MODIFIED Requirements

### Requirement: 风险列表查询

`GET /api/commits` SHALL 按 `risk_score` 降序返回提交列表，支持 `page`/`size` 分页（默认 1/20）与 `min_risk`/`model_name`/`start_time`/`end_time` 筛选；`items` SHALL 只取单个 `model_name` 的预测行，`model_name` 缺省 SHALL 取 `prediction` 表内模型中**版本序**（`version_key`，design D6）最大者，MUST NOT 跨模型混排（否则同一提交会翻出多条重复项）。`start_time`/`end_time` SHALL 按**闭区间** `[start, end]` 以 `committed_at` 过滤（契约三 2.0 区间语义）：**纯日期串**（`YYYY-MM-DD`）start 解释为当天 `00:00:00.000000`、end 解释为当天 `23:59:59.999999`（结束日含全天）；带时间分量的串按原样解析；带时区的串先转 UTC。

#### Scenario: 默认排序与分页

- **WHEN** 不带任何参数调用
- **THEN** `items` 按 `risk_score` 降序、返回第 1 页 20 条，`total` 为筛选后总数

#### Scenario: 筛选结果为空

- **WHEN** 筛选条件下没有任何提交
- **THEN** 返回 `code` 0、`items` 空数组、`total` 0 —— 空数据不是错误

#### Scenario: 纯日期串 end 含结束日全天

- **WHEN** 以 `start_time=2026-08-03&end_time=2026-08-03` 调用
- **THEN** 返回 `committed_at` 落在 2026-08-03 全天（含 09:00 等非整点时刻）的提交，MUST NOT 只取当天 00:00 整点

#### Scenario: 带时间分量的 end 按原样

- **WHEN** 以 `end_time=2026-08-03T08:59:59` 调用
- **THEN** 当天 09:00 的提交 MUST NOT 被包含（时间分量不被「收尾」规则改写）

### Requirement: 趋势聚合查询

`GET /api/trends` SHALL 按 `granularity`（枚举 `week` 默认 / `month`）聚合风险趋势；SHALL 支持可选参数 `start_time`/`end_time` 与 `model_name`（缺省取表内版本序最大模型）；时间过滤 SHALL 与风险列表同语义——**闭区间**、纯日期串 end 含结束日全天（契约三 2.0）；`high_risk_count` SHALL 由后端按**固定常量阈值 `risk_score >= 0.5`** 计算（本 change 不开放为请求参数 —— 契约三 §3 请求参数表未列该参数，见 design D10），MUST NOT 交由前端重算；`series` SHALL 只返回单个 `model_name` 的一组数据。

#### Scenario: 周粒度聚合

- **WHEN** 以默认参数调用
- **THEN** `series` 按周升序，每项含 `period`/`commit_count`/`avg_risk`/`high_risk_count`，`period` 格式形如 `2026-W30`

#### Scenario: 粒度取值非法

- **WHEN** 以 `granularity=day` 调用
- **THEN** 返回 40001（HTTP 400），message 指出参数名与合法枚举

#### Scenario: 时间范围内无数据

- **WHEN** 所选时间范围内没有任何提交
- **THEN** 返回 `code` 0、`series` 空数组 —— 空数据不是错误

#### Scenario: 周下钻纯日期串不丢结束日

- **WHEN** 以某 ISO 周的周一与周日纯日期串作为 `start_time`/`end_time` 调用
- **THEN** 该周七天的提交全部计入（`commit_count` 与看板同周期口径一致），MUST NOT 丢周日当天

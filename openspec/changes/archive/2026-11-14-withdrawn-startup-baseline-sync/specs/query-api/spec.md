## ADDED Requirements

### Requirement: PR 风险转译呈现

`GET /api/prs` SHALL 对每个 PR 返回其聚合风险的**等级**（高 / 中 / 低，阈值可配）与**一句话理由摘要**；理由 SHALL 基于该 PR 最高风险提交的特征 / SHAP 因子模板生成，MUST NOT 依赖 LLM 或外部调用。前端 PR 主视图 SHALL 以风险徽章呈现等级，hover 或展开显示原始概率与理由。

#### Scenario: 风险等级映射

- **WHEN** 某 PR 聚合风险为 0.73
- **THEN** 返回 `risk_level="高"`（按可配阈值），前端徽章显示高风险色，hover 显示原始概率 0.73

#### Scenario: 理由摘要生成

- **WHEN** 某 PR 最高风险提交由"大改动 + 新手作者"主导
- **THEN** `reason` 字段返回如"大改动（LA 高）+ 作者经验低"的模板化摘要，`MUST NOT` 为空且不调用外部模型

### Requirement: 模型切换、查看过滤与已预测覆盖

`GET /api/commits`（及 commit 详情）SHALL 支持 `model_name` 参数按其取对应 `prediction` 行；SHALL 支持 `since` / `until` 作为**查看过滤器**（按 `commit.committed_at` 过滤已预测结果，**MUST NOT 触发新预测**）。当某 `model_name` 对某 commit 缺预测行时，系统 SHALL 引导用户通过「补齐到最新」（catchup）补齐，MUST NOT 在前端提供按历史日期区间单独预测的手段。`GET /api/commits/coverage` SHALL 返回当前已预测的时间覆盖区间（每个 `model_name` 的 `[min_committed_at, max_committed_at]`），前端 SHALL 展示"已预测覆盖：起 ~ 止"并告知缺口，用户通过「补齐到最新」按钮由系统补齐。

#### Scenario: 按模型取数

- **WHEN** 以 `model_name=xgb_v1` 查询 commit 列表
- **THEN** 仅返回该模型下的风险分；若该模型对某 commit 缺行，前端可得知并引导至 catchup，MUST NOT 返回其它模型冒充

#### Scenario: 日期仅查看过滤

- **WHEN** 以 `since`/`until` 查询 commit 列表
- **THEN** 仅返回 `committed_at` 落在该窗口且已预测的 commit，`MUST NOT` 因筛选而触发对该区间的新预测

#### Scenario: 已预测覆盖可见

- **WHEN** 前端请求覆盖区间
- **THEN** 返回各模型已预测 `committed_at` 的最小/最大值；前端据此显示"已预测覆盖"与缺口，并提供「补齐到最新」入口

# query-api Specification

## Purpose

定义当前提交查询与趋势查询的只读行为。接口字段和筛选参数分别以 `docs/api/commits.md`、`docs/api/trends.md` 为准；模型级联清单见 `docs/api/models.md`。

## Requirements

### Requirement: 统一包络与错误码

`/api` 接口 SHALL 使用 `{ "code": 0, "message": "ok", "data": {...} }` 成功包络；错误业务码 SHALL 使用 40001、40100、40400、50000，并按 `docs/api/` 对应接口文件映射 HTTP 状态，MUST NOT 将内部异常细节回显。

#### Scenario: 成功响应
- **WHEN** 合法请求成功
- **THEN** HTTP 成功且 `code=0`，业务载荷位于 `data`

#### Scenario: 参数越界
- **WHEN** 以 `size=101` 调用 `GET /api/commits`
- **THEN** HTTP 400、`code=40001`，MUST NOT 返回分页数据

### Requirement: 接口鉴权

受保护的 `/api` 业务接口 SHALL 校验 `X-API-Key`，缺失或不匹配 SHALL 返回 HTTP 401、`code=40100`。公开健康探针是否要求鉴权以 `docs/api/health.md` 为准。

#### Scenario: 正确令牌
- **WHEN** 请求带正确 `X-API-Key`
- **THEN** 继续业务处理

#### Scenario: 错误令牌
- **WHEN** 请求未带令牌或令牌不匹配
- **THEN** 返回 40100，不泄露正确令牌

### Requirement: 风险列表查询

`GET /api/commits` SHALL 只读 `commit` 与选中模型的 `prediction`，支持 `page`、`size`、`model_name`、`start_time`、`end_time`、`q`，以及模型性能表所用 `with_features=1`、`is_test=1`；MUST NOT 接收已下线的 `min_risk`、`has_label` 或 `scope` 作为现行功能。缺省模型为已加载模型中 `version_key` 最大者。结果 SHALL 按 `risk_score DESC, commit_hash ASC` 排序，同一提交在同一模型下只出现一次。时间区间两端包含，纯日期结束值包含全天。

#### Scenario: 查询已预测提交
- **WHEN** 使用有效筛选条件查询风险列表
- **THEN** 返回命中且已预测的提交及准确的 `total`，分页排序稳定

#### Scenario: 筛选无结果
- **WHEN** 指定模型或时间范围没有预测行
- **THEN** 返回 `code=0`、`items=[]`、`total=0`，MUST NOT 伪造风险 0 行

### Requirement: 提交详情查询

`GET /api/commits/{commit_hash}` SHALL 返回提交元信息、所选模型预测时间与风险分、Kamei 14 维 log 特征、解释因子及 SZZ 真标签 `is_bug_inducing`；未打标为 `null`，MUST NOT 变成 0，也不返回已下线的人工 `label` 对象。

#### Scenario: 已有提交详情
- **WHEN** 查询存在且有预测行的提交
- **THEN** 返回该提交与单个模型的风险分、特征、解释和真实标签

#### Scenario: 尚未预测
- **WHEN** 提交存在但所选模型没有预测行
- **THEN** `risk_score` 与 `predicted_at` 为 `null`，MUST NOT 显示成零风险

### Requirement: 趋势聚合查询

`GET /api/trends` SHALL 按 `week` 或 `month` 聚合所选模型的已预测提交，时间筛选与列表一致；`high_risk_count` 按服务配置 `HIGH_RISK_THRESHOLD` 计算。查询只读，不触发预测。

#### Scenario: 周粒度
- **WHEN** 以默认参数查询
- **THEN** `series` 按周升序，含 `period`、`commit_count`、`avg_risk`、`high_risk_count`

#### Scenario: 无效粒度
- **WHEN** 以 `granularity=day` 查询
- **THEN** 返回 40001，MUST NOT 静默改成周粒度

### Requirement: 内部信息不回显

50000 的 `message` SHALL 使用固定文案；堆栈、SQL、路径与令牌仅能进入受控服务日志。

#### Scenario: 数据库故障
- **WHEN** 数据库连接失败
- **THEN** 响应不含连接串、SQL 和文件路径

#### Scenario: 模型文件损坏
- **WHEN** 查询触发相关内部异常
- **THEN** 响应不含模型文件路径，服务端保留诊断日志

### Requirement: Swagger 实现镜像

系统 SHALL 暴露 FastAPI OpenAPI schema；当前路径、参数和响应字段 SHALL 与 `docs/api/` 中的对应文件一致。

#### Scenario: 对照现行接口
- **WHEN** 导出 `/openapi.json` 并核对现行文档
- **THEN** 路径、字段、类型与枚举无偏离

#### Scenario: 文档仍指向旧路径
- **WHEN** 发现对已下线端点或已删除的旧版契约的引用
- **THEN** 在同一 PR 修正文档与规格，MUST NOT 将历史路径当作当前接口

### Requirement: 提交哈希大小写归一化

请求中的 `commit_hash` SHALL 先校验为 40 位十六进制串，再归一化为小写用于查库与响应；MUST NOT 放宽长度或字符集校验。

#### Scenario: 大写哈希命中
- **WHEN** 以同一已存在哈希的全大写形式请求详情
- **THEN** 与小写请求命中同一提交，回显小写哈希

#### Scenario: 非法哈希
- **WHEN** 哈希含非十六进制字符或长度错误
- **THEN** 返回 40001，MUST NOT 进入数据库查询

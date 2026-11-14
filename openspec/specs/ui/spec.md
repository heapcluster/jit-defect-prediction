# ui Specification

## Purpose

规定当前四页 Web 界面的共同边界。每页的字段和交互细节分别以 `docs/web_page/` 为准，接口以 `docs/api/` 为准。

## Requirements

### Requirement: 四页导航与真实数据

前端 SHALL 提供风险列表、提交详情、趋势看板和模型性能四个页面；风险分、趋势及模型指标 SHALL 读取后端接口，MUST NOT 在前端伪造数据或另算模型分数。页面定义见 `docs/web_page/README.md`。

#### Scenario: 四页可访问

- **WHEN** 用户打开四个现行页面并且后端有对应数据
- **THEN** 每页展示对应接口返回的内容，列表可进入所选提交的详情

#### Scenario: 后端无数据

- **WHEN** 查询成功但 `items` 或 `series` 为空
- **THEN** 页面展示明确空态，MUST NOT 把空数据显示为请求失败或风险 0

### Requirement: 模型选择与错误态

模型选择 SHALL 以 `GET /api/models` 的已登记清单为准；详情的显式模型选择 SHALL 传入 `model_name`，错误状态 SHALL 保留后端业务码，按相应页面显示可理解的提示。前端 MUST NOT 写死当前交付模型数量。

#### Scenario: 选择非默认模型

- **WHEN** 用户从模型清单选择一个非默认模型并打开提交详情
- **THEN** 详情请求带所选 `model_name`，页面显示该模型的预测而不混用默认模型

#### Scenario: 详情提交不存在

- **WHEN** 后端对详情请求返回 40400
- **THEN** 页面展示不存在状态与返回列表入口，MUST NOT 把它当成一般网络错误

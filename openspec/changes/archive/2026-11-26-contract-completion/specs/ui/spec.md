## ADDED Requirements

### Requirement: 模型性能按评估批次选图

模型性能页 SHALL 先获取 `batches[]`，提供“最新批次 / 具体批次”下拉；切换批次后按 `job_id` 拉取该批次图集与指标。不同批次的同类型图 MUST NOT 互相覆盖。

#### Scenario: 切换批次

- **WHEN** 用户在下拉中选择某评估批次
- **THEN** 页面只展示该批次的图与指标，最新批次为默认值

### Requirement: 数据链路视图

storage 页面 SHALL 提供“数据链路”视图，展示链路标题、时间、节点数、类型分布，可展开任务节点与产物，并提供整链删除二次确认。

#### Scenario: 查看并删除链路

- **WHEN** 用户展开链路并点击“整链删除”并确认
- **THEN** 调用删除端点；成功刷新链路与产物库；被外部引用时展示后端错误信息

### Requirement: 详情页内联定位

提交详情页 SHALL 在“缺陷定位及修复”普通板块内运行并展示定位结果，MUST NOT 跳转独立页面，标题 MUST NOT 显示功能编号 ⑦/⑧。独立路由 `/predict/explain` 与 `/predict/localization` MUST NOT 再提供。

#### Scenario: 内联运行定位

- **WHEN** 用户在详情页填写仓库路径并点击“运行定位”
- **THEN** 页面调用定位任务、展示行级可疑代码与修复建议，URL 保持详情页不变

# 系统测试计划

> **状态：待人工撰写（占位）。** 按课程 AI-R5，系统测试计划必须由测试负责人（neon）依据真实环境人工撰写并签字，AI 不得代写、不得代签。本文件只列出课程要求的结构，不含结论。

## 待撰写结构

| 章节 | 课程要求 |
|---|---|
| 测试范围 | 完整 Web 系统端到端全链路，黑盒为主；功能 + 非功能 |
| 测试策略 | 基于需求规格编写用例；每功能点覆盖正常 / 异常 / 边界；反向用例 ≥30%；重点用例标注 |
| 非功能 | 性能（JMeter/Locust）、兼容性（Chrome / Edge / Firefox ≥3）、安全（越权 / 注入 / 上传）、易用性 |
| 测试环境 | 见 [`../README.md`](../README.md) §6 产物与提交对照；以最终交付 SHA 为准 |
| 资源与进度 | 由 neon 分配，附现场演示安排 |
| 风险评估 | 模型权重不入库、浏览器与真实 MySQL 不能由 CI 代测等 |
| 进入 / 退出条件 | 人工判断并签字 |

可参考的实测材料：主线 7 步与异常场景记录见 [`execution_records/system-test-run.md`](execution_records/system-test-run.md)，13/13 异常场景实测见 [`execution_records/neon-test-execution.md`](execution_records/neon-test-execution.md)（E-19）。这些是执行记录，**不是计划**。

## 人工撰写输入索引（本文件只给材料链接，不含计划正文）

| 待撰写章节 | 可直接引用的实测材料 |
|---|---|
| 测试范围 | [`../../overview.md`](../../overview.md)、[`test_cases.md`](test_cases.md) §2 / §3 |
| 测试策略与用例统计 | [`test_cases.md`](test_cases.md) §1（24 + 6 条、反向 15/24 = 62.5%、★ 5 条） |
| 非功能测试口径 | [`performance/README.md`](performance/README.md)、[`test_cases.md`](test_cases.md) §3 |
| 缺陷口径 | [`bug_list.md`](bug_list.md) |
| 测试环境与基线 | [`execution_records/system-test-run.md`](execution_records/system-test-run.md) 抬头、[`../README.md`](../README.md) §6 |
| 执行证据 | [`execution_records/`](execution_records/)（主线 7 步、异常 13/13、6 张截图） |
| 资源分配 / 进度安排 / 进入退出条件 / 风险评估 / 签字 | **由 neon 人工判断并填写**，AI 不提供草案、不代签 |

按 AI-R5，上表只是材料索引；正式计划的范围界定、策略取舍、风险取舍与发布前判断必须由测试负责人依据实测撰写。

签字：__________　日期：__________

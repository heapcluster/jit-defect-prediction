# 验收测试方案

> **状态：待人工撰写（占位）。** 按课程 AI-R5，验收方案与验收结论必须由测试负责人（neon）人工撰写并签字；AI 不得代写、不得代签，不得代替「是否接受系统交付」的判断。

## 待撰写结构

| 章节 | 课程要求 |
|---|---|
| 验收范围 | 最终交付版本，前端界面到后端预测服务的完整系统 |
| 验收标准 | 功能验收、数据验收、界面验收、文档验收四类；阈值须量化（如准确率 ≥80%，阈值由人工确认） |
| 验收环境 | 见 [`../README.md`](../README.md) §6；须与实测证据同一 SHA |
| 人员角色分配 | 学生扮演「用户 + 验收方」，由 neon 组织 |
| 进度安排 | 现场演示时间、逐条确认与记录方式 |
| 通过标准 | 核心功能 100%、非核心 ≥90%、无致命/严重遗留、一般遗留 ≤3 个且有修复计划、文档齐备 |

验收用例不少于 15 条、覆盖四个类别，且须从最终用户视角编写（描述用户要做的事与期望看到的结果，而非代码断言）；用例表见 [`acceptance_cases.md`](acceptance_cases.md)。

## 人工撰写输入索引（本文件只给材料链接，不含方案正文）

| 待撰写章节 | 可直接引用的材料 |
|---|---|
| 验收范围 / 需求条目 | [`../../overview.md`](../../overview.md)、[`../../common/project-requirements.md`](../../common/project-requirements.md)、[`acceptance_cases.md`](acceptance_cases.md) §2「对应需求条目」列 |
| 验收用例与四类覆盖 | [`acceptance_cases.md`](acceptance_cases.md) §1 / §2（20 条：功能 9 / 数据 3 / 界面 4 / 文档 4） |
| 量化验收标准与通过条件 | [`acceptance_cases.md`](acceptance_cases.md) §3；**预测准确性阈值须由验收方人工确认，不得采用 AI 建议值** |
| 验收环境 / 被测 SHA | [`../README.md`](../README.md) §6；四类产物 SHA 须一致 |
| 取证方式 | [`execution_records/README.md`](execution_records/README.md)（A-01 ~ A-20 逐条截图 / 录屏） |
| 缺陷遗留口径 | [`defect_residual.md`](defect_residual.md)、[`../system_test/bug_list.md`](../system_test/bug_list.md) |
| 人员角色分配 / 进度安排 / 通过标准裁定 / 签字 | **由 neon 人工判断并填写**，AI 不提供草案、不代签 |

按 AI-R5，验收方案涉及「是否接受系统交付」的判断，必须由人工做出；本文件保持占位，不含结论。

签字：__________　日期：__________

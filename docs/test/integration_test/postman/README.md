# Postman Collection

**当前状态：本项目未采用 Postman，本目录留空占位。**

课程 §3.3 允许「Postman Collection 导出文件**或** pytest 测试代码」，本项目选择编程式集成测试：

| 交付物 | 位置 |
|---|---|
| 接口测试用例集（11 端点 × 四类场景、含逐条来源标注） | [`../endpoint_inventory.md`](../endpoint_inventory.md) §4 |
| 集成测试脚本实体副本（9 个 `.py`） | [`../scripts/README.md`](../scripts/README.md) |
| 接口测试报告（清单、35/35 结果、异常说明、AI/手写比例） | [`../report.md`](../report.md) §3、§10 |
| AI 提示词归档 | [`../prompts/`](../prompts/README.md) |

若后续补 Postman Collection，须在每个请求描述字段标注 `[AI生成]` / `[AI生成-人工修改]` / `[手写]`，业务断言人工复核，并在本目录登记导出文件名、被测 SHA 与来源；未归档提示词按 AI-R2 扣 3 分。

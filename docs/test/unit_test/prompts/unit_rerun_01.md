# 提示词：按最终提交复跑单元测试并刷新说明文档

## 基本信息

- 使用工具：CodeBuddy（DeepSeek-V4.1-Flash）
- 使用日期：2026-11-15
- 关联测试文件：`backend/tests/`（23 个 `test_*.py`）、`data_model/tests/`（16 个）、`frontend/tests/`（9 个 `*.spec.js`）、`infra/tests/`
- 关联文档：`docs/test/unit_test/unit_test_report.md`、`docs/test/overview.md` §4–§5

## 提示词原文

```text
参照项目现有规范和测试框架，尽可能完成全部可自动化执行的测试，并将测试结果与说明
按真人书写风格输出到 docs\test 目录下。对于需要人工介入或超出你能力范围的测试项，
请列出清晰的待办清单并引导我逐步完成。你无需负责提交 commit。

约束：
1. 不要改业务代码；测出来的问题记录到文档，不要顺手"修好"再宣布通过。
2. 每个数字必须来自本次真实执行，不允许沿用历史记录值。
3. 单元测试说明文档要包含：测试模块、用例数量、覆盖率数值、运行命令、
   AI/手写用例比例统计（不可追溯就写"待核"，禁止编造）。
4. 覆盖率要区分行覆盖、分支覆盖与 HTML 首页显示的综合值，别混着写。
```

追加的两条追问（同一会话）：

```text
后端 pytest 报 RuntimeError: Directory '...\backend\static' does not exist，
这是环境问题还是代码问题？请判定并在文档里写清楚复现路径。
```

```text
把覆盖率数字从 coverage 数据里核实一遍，不要只看 term 报告最后一行。
```

## 大模型输出摘要

- 定位到 conda 环境并直接用环境内解释器（`D:\workspace\env\miniconda3\envs\jit-defect-prediction\python.exe`），绕开 shell 未初始化 conda 的问题。
- 判定 `backend/static` 缺失属代码缺陷（`app/main.py:101` 无条件挂载），手工建目录后跑通，并登记为 BUG-01。
- 后端 `254 passed`、模型线 `162 passed`、前端 `59 passed`、基础设施 `8 passed`、CI 契约 `11 passed`；覆盖率从 `coverage json` 核实为行 87.2% / 分支 76.2% / 综合 85.2%。
- 产出按模块的用例分布表、覆盖率短板清单、来源标签统计（后端 12/23 文件有标签，模型线 1/16，前端 7/9）。

## 人工审核与修改记录

- 审核结果：**待人工审核**（本人未签）
- 修改内容：无人工修改；文档中的比例统计一律写「待核」，未补造数字
- 备注：本轮只跑用例，未新增或修改任何测试断言，故不涉及 AI-R4 的核心断言问题；文件头比例注释缺口仍按 #233 挂账

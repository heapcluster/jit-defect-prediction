# 单元测试提示词归档

按测试模块归档，每个文件含：基本信息、提示词原文、大模型输出摘要、人工审核与修改记录。

| 文件 | 覆盖范围 | 关联测试文件 |
|---|---|---|
| [`unit_predict_01.md`](unit_predict_01.md) | 后端接口、安全、契约、服务层 | `backend/tests/`（28 文件 / 279 条） |
| [`unit_preprocess_01.md`](unit_preprocess_01.md) | 数据链路、SZZ、训练切分、权重交付 | `data_model/tests/`（16 文件 / 163 条） |
| [`unit_frontend_01.md`](unit_frontend_01.md) | 前端纯函数与组件、infra 建库、CI 契约 | `frontend/tests/` + `infra/tests/` + `.github/ci/tests/`（84 条） |
| [`unit_rerun_01.md`](unit_rerun_01.md) | 按最终提交复跑并刷新说明文档 | 全部 |

## 使用工具

CodeBuddy（DeepSeek-V4.1-Flash），辅助生成用例骨架、参数化数据与 Mock 配置；核心业务断言由人工复核，记录见 [`../README.md`](../README.md)。

## 新增用例时的归档模板

```markdown
# 提示词：<用途>

## 基本信息
- 使用工具：<工具与版本>
- 使用日期：<YYYY-MM-DD>
- 关联测试文件：<路径>
- 关联文档：<路径>

## 提示词原文
<完整原文，保留约束与追问>

## 大模型输出摘要
<生成了哪些文件、多少用例、关键断言>

## 人工审核与修改记录
- 审核结果：<直接采纳 / 修改后采纳 / 弃用>
- 修改内容：<逐条说明改了什么，尤其核心断言>
- 备注：<来源标签如何标注>
```

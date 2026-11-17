# 提示词：前端与工程化单元测试用例生成（纯函数/组件契约/CI 契约）

> 用途：记录前端、基础设施与 CI 契约测试用例生成时使用的提示词与产出摘要，供审核与复现参考。
> 关联提交：`1d6b06c`。

## 基本信息

- 使用工具：CodeBuddy（DeepSeek-V4.1-Flash）
- 使用日期：2026-11
- 关联测试文件：`frontend/tests/`（10 个 `*.spec.js`，65 条）、`infra/tests/`（1 个文件，8 条）、`.github/ci/tests/`（2 个文件，11 条）
- 关联文档：`docs/web_page/`、`docs/api/`、`frontend/vite.config.js`
- 来源标注：`[AI生成-人工修改]`（AI 生成骨架，人工补充核心断言）

## 提示词原文

```text
你是前端与工程化测试工程师。为 JIT 缺陷预测系统的 Vue 3 前端、infra 建库脚本与 CI 契约编写单元测试。

业务背景：
- 前端四个页面：风险列表、提交详情、趋势看板、模型性能
- 风险阈值口径（D-10）：risk_score >= 0.5 → 高风险；>= 0.2 → 中等风险；其余 → 常规
- 错误码映射：40001 优先取 detail，40100/40400/50000 固定人话，超时单独文案
- 提交详情 SZZ 三态：1 → 「SZZ：引入缺陷」、0 → 「SZZ：非缺陷」、null → 「无 SZZ 标记」
- 14 项特征字段前后端必须逐字逐序一致（契约见 feature_order.txt）
- infra/setup_mysql.py 负责建库，需要可测的纯函数解析
- .github/ci/ci_scope.py 按变更路径决定跑哪条测试线

编写要求：
1. 前端用 vitest + @vue/test-utils，jsdom 环境；纯函数优先，组件用 mount 验证渲染契约
2. 每条用例覆盖正常、边界、异常；边界值要测"紧邻阈值"（如 0.1999、0.5、0.2）
3. 断言业务语义，不要只断言"渲染成功"
4. infra 与 CI 契约用 pytest / unittest，断言解析结果与 scope 判定
5. 文件头加来源标注注释（JS 用 // 前缀）

约束：
- 不改 frontend/src、infra/*.py 产品代码
- 不 mock 掉被测函数本身
```

## 大模型输出摘要

- 前端 10 个文件、65 条：
  - 工具与契约：`features.spec.js`（3）、`models.spec.js`（2）、`risk.spec.js`（7）、`datetime.spec.js`（5）、`errors.spec.js`（9）
  - 请求层：`api.spec.js`（10）、`request.spec.js`（6）
  - 组件：`CommitDetail.spec.js`（12）、`RiskList.spec.js`（5）、`syncProgress.spec.js`（6）
- infra：`test_setup_mysql_credentials.py`（8）
- CI 契约：`test_ci_contract.py`（4）、`test_ci_scope.py`（7）
- 合计 65 + 8 + 11 = 84 条，全部通过

## 人工审核与修改记录

- **审核结果**：修改后采纳
- **修改内容**：
  - `CommitDetail.spec.js` 补齐 SZZ `0 → 「SZZ：非缺陷」` 断言（原用例声称三态却只测两态）
  - `risk.spec.js` 合并重复断言，保留紧邻阈值 `0.1999` 用例
  - `api.spec.js` 测试名改为与断言一致（「空筛选时各参数保持 undefined」）
  - `features.spec.js` 路径改为基于 `import.meta.url` 推导，不再依赖 `process.cwd()`
  - 7 个前端文件与 2 个 CI 文件补齐 §2.1 文件头
- **核心断言复核**：风险阈值、错误码映射、SZZ 三态、14 维字段已与 `src/` 实现比对，见 [`../README.md`](../README.md)

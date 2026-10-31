# realtime-pr-prediction — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无独立 design.md ｜ 规格：`specs/predict-api/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-26 ｜ 状态：进行中（以任务勾选和证据为准）
> 关联需求：无（PR 预测能力）
> 统一格式见 `docs/common/openspec-task-template.md`；末尾「测试与验证」为强制板块。

## 1. 后端 PR 实时预测能力

- [x] 1.1 `backend/app/github.py`：open PR 清单 / 单 PR 元信息 / PR 提交清单三个只读客户端（纯标准库 urllib，token 走 GITHUB_TOKEN 不回显）
- [x] 1.2 `backend/app/api/prs.py`：POST /api/sync-prs（逐 PR fetch head → 逐提交复用单条多模型链 → skipped 隔离）、GET /api/prs（聚合最高风险）、GET /api/prs/{number}（提交级明细）
- [x] 1.3 `backend/app/main.py` 注册路由；`backend/app/config.py` 新增 GITHUB_REPO（默认 apache/camel）
- [x] 1.4 `backend/app/schemas.py` 三个响应模型，OpenAPI 携带字段（镜像测试可比对）
- [x] 1.5 `backend/tests/test_prs_api.py` 8 条：聚合口径、只读端点不依赖 SOURCE_REPO（回归）、单 PR 失败隔离、未预测提交 null、未知模型 40001、limit 越界 40001、逐 PR/逐提交 skipped 形态

## 2. 契约与文档

- [x] 2.1 [历史版 `docs/backend/api-spec.md`](https://github.com/heapcluster/jit-defect-prediction/blob/100008e787c8902c35760c9cef6d61d279d921b7/docs/backend/api-spec.md) §6~§8 登记三条端点（v1.7，路径数 5→8），§4 在线模型清单口径同步回填 8 模型
- [x] 2.2 `backend/.env.example` 补 GITHUB_REPO / GITHUB_TOKEN 注释行
- [x] 2.3 本 change 提案（openspec/changes/realtime-pr-prediction/）补齐 —— 功能先行落地后的追溯补录

## 3. 验收

- [ ] 3.1 本机实测：对 Camel 真实 open PR 跑 POST /api/sync-prs（小 limit），GET /api/prs 返回聚合风险并与库内行对账
- [ ] 3.2 CI 全绿（ruff + pytest + openspec validate）
- [ ] 3.3 非功能记录：单 PR 多提交 × 8 模型的耗时实测值登记进任务证据，MUST NOT 声称 500ms 靶子

## 4. 后续（另行 change，不在本条范围）

- [ ] 4.1 PR 状态跟踪（open/merged/closed 标记，不删行；realtime-commit-sync tasks 4.1 同款）
- [ ] 4.2 定时器与同步频率配置化
- [ ] 4.3 前端 PR 页面接 GET /api/prs 全量字段与「同步最新 PR」按钮（已在飞，随前端线 PR 合入）

## 测试与验证（强制板块）

### 1. 单元测试

- 覆盖对象：参数校验、数据选择与失败隔离；测试文件：`backend/tests/test_prs_api.py`。
- 复现命令：在 `backend/` 运行 `python -m pytest tests/test_prs_api.py -q`。
- 当前提交结果待 CI 取证；本次格式整理未重新执行。

### 2. 集成测试

- 范围：路由 → 特征抽取 → 模型推理 → 数据库写入与查询。
- 复现步骤：按 `docs/common/local-runbook.md` 起服务，调用本 change 的同步接口并核对查询结果。
- 真实数据和权重的全链路证据尚未登记。

### 3. 验收测试

- 依据：`specs/predict-api/spec.md` 的 SHALL/MUST 与 Scenario；提案校验命令：`openspec validate realtime-pr-prediction --strict --no-interactive`。
- 正常、异常及幂等场景须留请求响应和数据库对账；当前未登记现场通过记录。

### 4. 非功能验证

- 触及耗时和并发可靠性；真实环境须记录耗时、并发保护及失败隔离。
- 当前没有可复核实测数字，不能把估算当作验收结果。

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划 |
|---|---|---|---|
| 真实联调及耗时证据 | 当前无可复核记录 | backend 吕建江 | 联调验收前补证据与运行链接 |
| 已勾选任务的当前提交回归 | 格式整理不等于重新验证 | backend 吕建江 | CI 成功后回填运行链接 |

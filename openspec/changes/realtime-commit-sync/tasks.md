# realtime-commit-sync — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无独立 design.md ｜ 规格：`specs/predict-api/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-25 ｜ 状态：进行中（以任务勾选和证据为准）
> 关联需求：无（同步能力）
> 统一格式见 `docs/common/openspec-task-template.md`；末尾「测试与验证」为强制板块。

## 1. 后端同步能力

- [x] 1.1 `backend/app/api/sync.py`：`POST /api/sync`（fetch → HEAD 可达性处理 → 挑新哈希 → 逐条复用单条预测链 → 汇总返回）
- [x] 1.2 禁代理 fetch（`-c http.proxy= -c https.proxy=`）、git 子进程超时 180s、并发互斥锁
- [x] 1.3 `backend/app/main.py` 注册路由；`SYNC_ON_STARTUP=1` 时启动后台预同步（失败不阻塞启动）
- [x] 1.4 `backend/tests/test_sync_api.py` 7 条：挑新纯函数、禁代理参数、SOURCE_REPO 缺失 40400、limit 越界 40001、端到端幂等（二次 new=0）、不可达提交计入 skipped、并发拒绝

## 2. 契约与文档

- [ ] 2.1 `docs/backend/api-spec.md` 补 `/api/sync` 一节（请求/响应/错误码/上限）——归后端线吕建江
- [ ] 2.2 `docs/common/local-runbook.md` §4 补 `SYNC_ON_STARTUP` 与同步用法
- [ ] 2.3 `backend/.env.example` 补 `SYNC_ON_STARTUP=` 注释行

## 3. 验收

- [ ] 3.1 本机实测：`POST /api/sync` 对已同步库返回 `new=0`（幂等）；对含新提交的仓库返回预测明细并入库
- [ ] 3.2 CI 全绿（ruff + pytest，覆盖率口径不变：不删既有用例）
- [ ] 3.3 非功能记录：单条同步时延实测值（浅历史 ≈3s/条）登记进任务证据，MUST NOT 声称 500ms 靶子

## 4. 后续（另行 change，不在本条范围）

- [ ] 4.1 PR 状态跟踪（GitHub API：open/merged/closed → `pr_state` 标记，不删行）
- [ ] 4.2 定时器（APScheduler）与同步频率配置化
- [ ] 4.3 前端「同步最新提交」按钮 + 同步结果提示

## 测试与验证（强制板块）

### 1. 单元测试

- 覆盖对象：参数校验、数据选择与失败隔离；测试文件：`backend/tests/test_sync_api.py`。
- 复现命令：在 `backend/` 运行 `python -m pytest tests/test_sync_api.py -q`。
- 当前提交结果待 CI 取证；本次格式整理未重新执行。

### 2. 集成测试

- 范围：路由 → 特征抽取 → 模型推理 → 数据库写入与查询。
- 复现步骤：按 `docs/common/local-runbook.md` 起服务，调用本 change 的同步接口并核对查询结果。
- 真实数据和权重的全链路证据尚未登记。

### 3. 验收测试

- 依据：`specs/predict-api/spec.md` 的 SHALL/MUST 与 Scenario；提案校验命令：`openspec validate realtime-commit-sync --strict --no-interactive`。
- 正常、异常及幂等场景须留请求响应和数据库对账；当前未登记现场通过记录。

### 4. 非功能验证

- 触及耗时和并发可靠性；真实环境须记录耗时、并发保护及失败隔离。
- 当前没有可复核实测数字，不能把估算当作验收结果。

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划 |
|---|---|---|---|
| 真实联调及耗时证据 | 当前无可复核记录 | backend 吕建江 | 联调验收前补证据与运行链接 |
| 已勾选任务的当前提交回归 | 格式整理不等于重新验证 | backend 吕建江 | CI 成功后回填运行链接 |

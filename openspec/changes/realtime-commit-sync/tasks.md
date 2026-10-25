# Tasks

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

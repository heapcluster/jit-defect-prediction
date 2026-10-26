# Tasks

## 1. 后端 PR 实时预测能力

- [x] 1.1 `backend/app/github.py`：open PR 清单 / 单 PR 元信息 / PR 提交清单三个只读客户端（纯标准库 urllib，token 走 GITHUB_TOKEN 不回显）
- [x] 1.2 `backend/app/api/prs.py`：POST /api/sync-prs（逐 PR fetch head → 逐提交复用单条多模型链 → skipped 隔离）、GET /api/prs（聚合最高风险）、GET /api/prs/{number}（提交级明细）
- [x] 1.3 `backend/app/main.py` 注册路由；`backend/app/config.py` 新增 GITHUB_REPO（默认 apache/camel）
- [x] 1.4 `backend/app/schemas.py` 三个响应模型，OpenAPI 携带字段（镜像测试可比对）
- [x] 1.5 `backend/tests/test_prs_api.py` 8 条：聚合口径、只读端点不依赖 SOURCE_REPO（回归）、单 PR 失败隔离、未预测提交 null、未知模型 40001、limit 越界 40001、逐 PR/逐提交 skipped 形态

## 2. 契约与文档

- [x] 2.1 `docs/backend/api-spec.md` §6~§8 登记三条端点（v1.7，路径数 5→8），§4 在线模型清单口径同步回填 8 模型
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

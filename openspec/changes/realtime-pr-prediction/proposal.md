# 拉取 Camel open PR 并实时预测入库

## Why

`realtime-commit-sync`（`POST /api/sync`）解决了「主干新提交」的实时预警，但评审真正关注的**入口是 PR**：Camel 的缺陷引入提交在合入主干前都活在 open PR 里，等 sync 到主干时预警已经晚了一步。同时前端三个页面只覆盖主干提交，看不出来「哪个 PR 危险」。

本 change 把「拉 open PR → 取 PR 内提交 → 现算特征并逐模型预测入库 → 按 PR 聚合风险」固化为后端能力，与 `realtime-commit-sync` 同纪律（复用单条预测链、冻结错误码、逐条失败不中断）。

## What Changes

- 新增 `POST /api/sync-prs?limit=N`（N 默认 10，上限 50）：拉 GitHub 公开仓库 open PR 清单 → 逐 PR `git fetch origin pull/<n>/head`（仅取对象、不 checkout，`SOURCE_REPO` 检出状态不变）→ 取该 PR 提交清单 → 逐提交**复用单条多模型链路**（一次现算特征、逐模型打分落 `prediction`）。
- 新增 `GET /api/prs`：open PR 聚合风险列表（`risk_score` 取该 PR 各提交在指定模型下的最高分），**纯只读**，不依赖 `SOURCE_REPO`。
- 新增 `GET /api/prs/{number}`：单个 PR 的提交级风险明细，**纯只读**，不依赖 `SOURCE_REPO`。
- 新增 `GITHUB_REPO`（默认 `apache/camel`）与既有 `GITHUB_TOKEN`（可选，提升匿名限额）两个配置项。

## Capabilities

### Modified Capabilities

- `predict-api`: 新增 PR 实时预测三条端点（路径数 5→8）。`sync-prs` 为编排触发，MUST NOT 引入新的预测口径或绕过单条链路的幂等与校验；两条查询端点 MUST NOT 依赖 `SOURCE_REPO`（数据来自 GitHub API + `prediction` 表），单 PR 失败 MUST 计入 `skipped` 而非整端 50000。

## Impact

- 代码：`backend/app/github.py`（新增，纯标准库 urllib 只读客户端）、`backend/app/api/prs.py`（新增）、`backend/app/main.py`（注册路由）、`backend/app/config.py`（`GITHUB_REPO`）、`backend/app/schemas.py`（三个响应模型）、`backend/tests/test_prs_api.py`（新增 8 条）。
- 文档：`docs/backend/api-spec.md` §6~§8（v1.7 已登记）；`backend/.env.example` 补 `GITHUB_REPO=`/`GITHUB_TOKEN=` 注释行。
- 依赖：无新第三方依赖（GitHub API 经标准库 urllib）。

## 不做什么

- **不做 PR 状态跟踪与清理**（open/merged/closed 映射、按状态删库）——预测对象是 commit；`realtime-commit-sync` 的 proposal 已把该事项列为后续 change，本 change 沿用其结论。
- 不做 webhook / 定时器；不把仓库路径开放给客户端；不承诺同步端点 500ms 靶子（`limit=30` 必然超过 10s，调用方须放宽超时）。
- 不引入新的预测口径、不改 `prediction` 表结构。

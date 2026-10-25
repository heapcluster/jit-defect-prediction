# 批量同步最新提交并在线预测

## Why

当前「新提交在线预测」是**单条、按需**的：调用方对每个新哈希手工调 `POST /api/predict`（且需人工先 fetch 仓库）。对一个定位为「在缺陷进入主干前预警」的在线服务而言，这既不符合实时预警的产品预期，也不可运营——上游每天约 50~100 条新提交，人工逐条触发不可持续。本 change 把「fetch 最新提交 → 挑出库中尚无的哈希 → 逐条现算特征并预测入库」固化为后端一个批量同步能力。

## What Changes

- 新增 `POST /api/sync?limit=N`（N 默认 10，上限 50）：对服务端 `SOURCE_REPO` 执行 `git fetch`（经命令行参数禁用代理，不依赖全局配置）、确保最新提交 HEAD 可达（不可达时 detach 到新 tip）、挑出库中不存在的新哈希，**逐条复用 `POST /api/predict` 现行单条链路**（extract → upsert → 幂等写 `prediction`）。
- 可选 `SYNC_ON_STARTUP=1`：服务启动后后台预同步一次（失败只记日志，不阻塞启动）。
- 单条失败（如提交不可达 40400）计入 `skipped`，不中断整批；无新提交时幂等返回 `new=0`。
- 并发保护：同一时刻仅允许一个同步任务（持锁中再进入返回 50000）。

## Capabilities

### Modified Capabilities

- `predict-api`: 新增批量同步端点 `POST /api/sync`，复用单条预测链与冻结错误码集合（0/40001/40400/50000）；本端点为编排触发，MUST NOT 引入新的预测口径或绕过单条链路的幂等与校验规则。

## Impact

- 代码：`backend/app/api/sync.py`（新增）、`backend/app/main.py`（注册路由 + 可选启动同步）、`backend/tests/test_sync_api.py`（新增 7 条）。
- 文档：`docs/backend/api-spec.md` 需补 `/api/sync` 一节（归后端线吕建江，本 change 合入后落实）；`docs/common/local-runbook.md` §4 补「SYNC_ON_STARTUP」与同步用法一行。
- 依赖：无新第三方依赖（git 经 subprocess 调用）。

## 不做什么

- **不做 PR 状态跟踪与清理**（open/merged/closed 映射、按状态删库）——预测对象是 commit，被 close 的 PR 其 head commit 仍是真实提交，删行会破坏 `prediction` 幂等契约与趋势完整性；如需状态标记另立 change（需 GitHub API 集成）。
- 不做 webhook 接收；不把仓库路径开放给客户端；不在本端点引入绕过单条链路的批量直写。
- 不承诺同步端点 500ms 靶子（单条扫描时延取决于 SOURCE_REPO 历史规模，首次全历史扫描为分钟级）。

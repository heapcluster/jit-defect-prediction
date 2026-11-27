# remove-dev-bootstrap — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/db-schema/spec.md`
> 负责人：backend（owner 口径落地）｜ 创建：2026-10-26 ｜ 状态：已实现并归档
> 用户故事：无（口径收紧：空库一律按需现算，杜绝提前灌库）

## 1. 规格 delta

- [x] 1.1 `db-schema`：MODIFIED「实时同步入库」—— 撤销例外段，恢复完整禁令，新增「空库首启」Scenario
- [x] 1.2 `db-schema`：REMOVED「本地开发数据初始化」（Reason / Migration 指向按需现算）

## 2. 代码

- [x] 2.1 删除 `infra/bootstrap_dev.py`（CSV 直灌）
- [x] 2.2 保留并验证标准链路：`POST /api/sync`（现算特征 → 真实权重预测 → 逐条落库）与 `POST /api/sync-prs`

## 3. 前端加载台

- [x] 3.1 `RiskList.vue`：空库/空筛选时显示同步引导卡（成本说明 + 数量选择 + 分批同步 + 逐批进度），完成后自动刷新列表
- [x] 3.2 `PrList.vue`：PR 无预测时提示触发 `POST /api/sync-prs`，加载中文案写明现算成本
- [x] 3.3 `PrDetail.vue`：提交无预测行时给「同步该 PR」引导

## 4. 文档

- [x] 4.1 `README.md` §7.3：两步跑起来（配 `.env` → `setup_mysql.py` → 起服务），数据靠界面同步，撤 bootstrap
- [x] 4.2 `docs/backend/mysql-setup.md`：撤 §4.4 初始化脚本，改为「空库 → 界面同步」说明
- [x] 4.3 `docs/common/local-runbook.md`：撤 bootstrap 行

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 前端视图改动（模板与样式）；后端仅删文件 |
| 测试文件 | `frontend/tests/*.spec.js`（26 条） |
| 用例数与结果 | 26 passed；`eslint` 0 问题；`vite build` 成功 |
| 复现命令 | `cd frontend && npm run test:unit && npm run lint` |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 清空四表 → 界面触发同步 → 数据逐条进来（真现算真预测） |
| 测试文件 | 无新增自动化（一次性环境验证） |
| 用例数与结果 | `POST /api/sync?limit=10` → `new=10`、`predicted=10`、`skipped=0`、156s（首次含全量历史扫描） |
| 复现命令 | `TRUNCATE` 四表后 `curl -X POST ".../api/sync?limit=10"` |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `db-schema`「空库首启」Scenario + 移除项的 Migration |
| 用例数与结果 | 通过：空库时查询端点 `code=0` 空列表；界面同步后列表/详情/趋势有数据 |
| 证据归档 | Playwright 实拍（加载台 → 同步中 → 列表有数据） |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是（现算成本透明化） | 加载台写明「每条约 15 秒」，10 条约 2.6 分钟 |
| 安全 | 否 | 同步仍需 `X-API-Key`；SOURCE_REPO 路径不接受请求方传入 |
| 可靠 | 是 | fetch 失败仍可对本地索引同步（`GIT_PROXY` 修复）；单条失败计入 skipped |
| 易用 | 是 | 空库不再是一张白屏，有明确的下一步 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 现算 15s/条，大批量耗时长 | 每条都要全量 `git log` 扫描构建历史索引 | backend | 可加持久化缓存（另立 change） |
| `.env` 需 `SOURCE_REPO`/`GIT_PROXY` 才能同步 | 现算依赖本地索引与网络 | backend | README 已写 |
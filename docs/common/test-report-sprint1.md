# 测试报告 · Sprint 1（快照 2026-10-13）

> 依据 `common/test-plan.md` §5 的report 约定产出。Sprint 1 于 10/23 结题，本文件为**中期快照**，结题前更新一次。
> 维护：蒋励（统稿）｜ 各线证据按包归集：`backend/evidence/`、`frontend/evidence/`、`model/evidence/`。

## 1. 执行环境（如实记录，不挑好看的版本）

| 项 | 值 |
|---|---|
| Python | **3.12.7 已复跑通过**（与 `backend/requirements.txt` 声明的 3.12.x 一致；PR #74 `0cad776`，45 passed / 0 failed）。此前 3.14.3 的临时验证结果仅作参考 |
| pytest | 9.1.1 |
| 数据库 | SQLite 内存库（`backend/tests/conftest.py` 按 `api-spec.md` §5 variant 口径） |
| 模型 | fixture 决策树（`fixture_v1`/`fixture_v2`），不依赖真实 `.pkl`，离线可跑 |
| 前端 | **已执行** —— Node v24.14.0 + npm 11.9.0；`npm install` 装齐 181 包后实跑（`npm ci` 因 dev server 占用 node_modules 未能完成，等价改用 install） |

## 2. 执行结果

| 层 | 命令 | 用例数 | 通过 | 失败 | 说明 |
|---|---|---|---|---|---|
| 单元 · 后端 | `cd backend && python -m pytest -q` | **87** | 87 | 0 | 原 39 条 + 2026-10-13 新增 48 条安全/边界用例 |
| 单元 · 模型 | `cd data_model && python -m pytest -q` | **8** | 8 | 0 | 契约一致性（14 项列名/顺序/交付清单/`feature_version`） |
| 单元 · 前端 | `cd frontend && npm run test:unit` | **4** | 4 | 0 | vitest 用例 `tests/risk.spec.js` 覆盖 D-10 阈值口径（0.5/0.3 边界） |
| 集成 | — | 0 | — | — | 无正式方案（`test-plan.md` §4.2 已列 T-IT-01~03，Sprint 2 执行） |
| 系统 | — | 0 | — | — | 仅 `repo/demo-script-sprint1.md` 手工脚本，待联调后跑 |
| 非功能 | — | 0 | — | — | 性能分位数与安全截图 Sprint 3 出（`nfr-evidence-scripts`） |

### 2.1 后端新增 48 条覆盖什么（`backend/tests/test_security_boundaries.py`）

| 分组 | 条数 | 对应用例编号 |
|---|---|---|
| 鉴权边界（四接口缺令牌、空/空白/大小写/超长/前缀令牌、不提示哪一位错） | 12 | T-NF-02 |
| 查询参数边界（`page`/`size`/`min_risk`/时间非法 → 40001；边界合法值不误判） | 19 | T-BE-05 |
| 详情 / 预测 / 趋势边界（哈希长度、非十六进制、缺字段、模型不在清单、粒度枚举） | 16 | T-BE-05 / T-ST |
| 信息泄露断言（响应体不含 Traceback / SELECT / sqlalchemy / .py / 路径 / site-packages） | 4 | T-NF-02 |

### 2.2 模型线新增 8 条覆盖什么（`data_model/tests/test_feature_contract.py`）

把**四个来源**钉在同一份有序 14 项清单上：契约文档 `docs/model/feature-columns.md` §三、实现 `FEATURE_FIELDS`、后端装配 `FEATURE_COLUMNS`、交付清单 `feature_order.txt`；另含 `feature_version=v1`、交付模型恰为 3 个、清单内 `.pkl` 真实存在、契约无 14 项之外列名。

## 3. 覆盖率

**已在 main 完成实测**（PR #74 `0cad776`，2026-10-16 合入）：`pytest-cov==7.1.0` 已入 `backend/requirements.txt`，在 Python 3.12.7 上实测后端**行覆盖 84%**（600 stmts / 95 miss），超过 `test-plan.md` §5 的 Sprint 2 目标 ≥60%。证据：`backend/scripts/evidence/coverage-2026-10-16.md`；Sprint 3 ≥75% 目标待后续提升。

> ⚠️ **基线口径提醒**：上述 84% 是在**不含本 PR 的 `backend/tests/test_security_boundaries.py`（48 条）**的 main 上测得。本 PR 合入后后端测试将从 45 条增至 93 条，**覆盖率须重测后另出证据文件**，不在旧文件上倒填数字。

## 4. 已知未执行 / 阻塞项

| # | 事项 | 阻塞原因 | 归属 |
|---|---|---|---|
| 1 | ~~前端单测与 `npm run lint` / `npm run build`~~ **已完成** | `npm install` 装齐依赖后实跑：test:unit 4 passed / lint 0 error / build ✓ | 刘帅华 ✅ |
| 2 | 前后端联调（T-IT-01~03） | 需先后端 `:8000` + 前端 dev + 真实数据（跑数据线 01–04） | 刘帅华 + 吕建江 |
| 3 | 系统测试（T-ST-01~05） | 依赖 2；演示录屏同此 | 蒋励 |
| 4 | 性能分位数（T-NF-01） | 压测脚本在 `nfr-evidence-scripts`，Sprint 3 出证 | 吕建江 |
| 5 | ~~覆盖率测量~~ **已完成** | PR #74：`pytest-cov==7.1.0`，Python 3.12.7 实测行覆盖 84%（600/95），证据 `backend/scripts/evidence/coverage-2026-10-16.md` | 吕建江 ✅ |
| 6 | ~~在 Python 3.12 复跑全量~~ **已完成** | PR #74：3.12.7 全量复跑 45 passed / 0 failed | 吕建江 ✅ |

## 5. 与 `test-plan.md` §7 退出准则的差距（Sprint 3 验收前必须清零）

| # | 退出准则 | 当前 | 差距 |
|---|---|---|---|
| 1 | 四层用例全部执行 | 单元 2/3 层已跑，集成/系统/非功能未跑 | 缺 3 层 |
| 2 | 每核心功能 1 正向 + ≥1 异常通过证据 | 后端已覆盖；前端已写未跑；模型线靠复现一致性 | 前端待跑 |
| 3 | ≥1 条端到端集成/系统测试通过并留录屏 | 无 | 缺 |
| 4 | ≥2 项非功能出验证证据 | 方案在、证据未出 | 缺 |
| 5 | 缺陷处置记录可导出、五项齐全 | 已建 `repo/defect-records.md` 索引（11 项） | 需与 GitHub Issue 核对 |
| 6 | CI 门禁跑通、单测随 PR 自动执行 | `.github/workflows` 为空（E1 未开始） | 缺 |

## 6. 本轮（2026-10-13）测试侧改动清单

- 新增 `data_model/tests/test_feature_contract.py`（8 条）
- 新增 `backend/tests/test_security_boundaries.py`（48 条）
- 新增 `frontend/src/__tests__/contract.test.js`（vitest，T-FE-01~03）
- `frontend/package.json` 增 `test:unit` script 与 `vitest` devDependency
- 新增 `common/test-plan.md`（测试总纲）、本报告
- 消除三处口径矛盾：`training-eval.md` §7「可复现优先于单测」↔ `engineering.md` §3 CI 单测承诺；`collaboration.md` §7 把 CI 列入「明确不做」↔ `engineering.md` §3

# 测试方案（跨包 · 四层测试总纲）

> 归属：课程《项目要求》Sprint 2「单元测试报告等」/ Sprint 3「完成功能、集成、系统等测试 + 问题/缺陷处置记录 + 至少两项已验证的非功能需求测试」
> 维护：蒋励（统稿）｜ 供稿：吕建江（后端/集成）、刘帅华（前端/联调）、蒋励（模型）、苏哲勋（工程/缺陷）
> 依据：`common/acceptance-overview.md`（验收板块）、`design/non-functional.md`（NFR）、`repo/defect-management.md`（缺陷流程）、`backend/api-spec.md`（契约三 v1.4）
> **本文件是测试唯一入口**：各包 `acceptance.md` 只做本线细化，不重复总纲；飞书《产品设计文档》「六、测试方案」为本文件的指针。

---

## 0. 为什么单独一份

课程「软件测试实践」占 40 分。此前测试内容散落在 4 个 `acceptance.md` + `design/engineering.md` §3 + `repo/demo-script-sprint1.md`，**无统一范围、策略、入口与退出准则**，且存在三处自相矛盾（模型线「可复现优先于单测」vs CI 承诺跑模型单测；前端 F6 要求有测试但 `frontend/` 下零测试文件；`repo/collaboration.md` §7 把 CI 列入「明确不做」而 `engineering.md` §3 已设计 CI 门禁）。本文件收口这三处。

## 1. 测试范围与分层

| 层 | 对象 | 负责 | 现有资产 | 目标 |
|---|---|---|---|---|
| **单元测试** | 后端四接口 / 鉴权 / ingest / mirror / model_registry；模型 14 特征口径 + `joblib.load` 加载 + SHAP 键名；前端三态 / 错误码 / 字段映射 | 吕建江、蒋励、刘帅华 | `backend/tests/` 9 个文件 **87 条已跑绿**；`data_model/tests/test_feature_contract.py` **8 条已跑绿**；`frontend/src/__tests__/contract.test.js` 已写（vitest，待 `npm ci` 后跑） | Sprint 2 补集成用例 + 覆盖率 |
| **集成测试** | API ↔ MySQL ↔ 前端三页面一条完整链路 | 吕建江 + 刘帅华 | `frontend/implementation.md` 联调记录 | Sprint 2 |
| **系统测试** | 端到端 1 条主链路 + 异常输入 + 8 模型切换 + 回归 | 蒋励（演示） | `repo/demo-script-sprint1.md` | Sprint 1 起跑，Sprint 3 收口 |
| **非功能测试** | 性能（p95<500ms）、安全（缺令牌 / 畸形参数）、可靠、易用 | 吕建江 + 刘帅华 | `backend/api-spec.md` §四、`design/non-functional.md` | Sprint 3 出证据 |

## 2. 测试环境与数据前置（写进方案，避免「跑不起来」）

| # | 前置 | 依据 |
|---|---|---|
| 1 | 数据：按 `model/data-pipeline.md` 九步跑 01–04，产出 `split_szz_train/test.csv`（7625 / 3268，种子 42，时间序切分） | `model/data-pipeline.md` |
| 2 | 模型：`data_model/models/` 内交付 `.pkl` + `feature_order.txt`；后端按 `joblib.load` 口径加载 | `model/training-eval.md` §6 |
| 3 | 库表：`design/database.md` 四表建好；测试环境用 SQLite，类型按 `api-spec.md` §5 variant 口径 | `design/database.md`、`backend/api-spec.md` §5 |
| 4 | 服务：后端 `:8000`、前端 `npm run dev`（`/api` 代理指向 `:8000`） | `frontend/pages.md` |
| 5 | 密钥：`X-API-Key` 走构建期环境变量 `VITE_API_KEY`，**不入库** | `backend/api-spec.md` §一 |

## 3. 用例设计规则（课程硬要求）

1. 每个核心功能：**1 条正向 + ≥1 条异常/边界**；至少覆盖 **1 条核心端到端业务链路**的集成或系统测试。
2. 用例编号 `T-<线>-<序号>`（如 `T-BE-01`），并在 `repo/user-story-traceability.md` 挂回 User Story，保证「用例 → 故事 → 规格」可追。
3. 异常用例至少覆盖五类：空数据、非法参数、缺令牌/越权、目标不存在、服务内部错误（**不得回显堆栈/SQL/路径**）。
4. 数据切分禁随机（时间序）；复现性要求「别人照命令跑出同一份统计（±0）」。
5. **只勾 tasks ≠ 合格**：每条用例须留运行证据（日志/截图/录屏）才能标通过。

## 4. 各层用例清单（最小集，Sprint 2 前补全）

### 4.1 单元测试

| 编号 | 用例 | 期望 | 状态 |
|---|---|---|---|
| T-BE-01 | `GET /api/commits` 正常分页 | 200，`data.total/items[]` 字段与契约一致，按 `risk_score` 降序 | ✅ 已有 `backend/tests/test_commits_api.py` |
| T-BE-02 | `GET /api/commits` 空结果集 | 200 且 `data.items === []`、`total === 0`（非 404） | ✅ 已有 |
| T-BE-03 | `POST /api/predict` 正常预测 | 返回 `risk_score` + `explanation[]`，`model_name` 与入参同名 | ✅ 已有 `test_predict_api.py` |
| T-BE-04 | 缺 `X-API-Key` | 401 `code=40100`，不回显内部信息 | ✅ 已有 `test_auth_errors.py` |
| T-BE-05 | 畸形参数（`commit_hash` 非法 / `page=0` / `size=101` / `min_risk=1.5` / 非法时间 / 粒度枚举） | 400 `code=40001`，`message` 指出参数；边界合法值不误判 | ✅ 已有 `backend/tests/test_security_boundaries.py`（48 条） |
| T-BE-06 | 模型注册表加载（`joblib.load` 口径） | 8 个 `model_name` 均可加载，特征数自检通过 | ✅ 已有 `test_model_registry.py` |
| T-MO-01 | 14 项特征键名与 `feature-columns.md` 逐字一致 | 键名集合相等、顺序一致（四处来源同一份有序清单） | ✅ `data_model/tests/test_feature_contract.py`（8 passed） |
| T-MO-02 | 交付模型 `joblib.load` + 特征数自检 | 加载成功，特征数与 `feature_order.txt` 一致 | ✅ `backend/tests/test_model_registry.py` |
| T-MO-03 | SHAP 解释键名可回溯到 14 特征 | 每条 `explanation` 的键名 ∈ 14 特征 | ✅ `backend/tests/test_model_registry.py::_explain_of` |
| T-FE-01 | 三态（加载中 / 空数据 / 失败） | 空数据显示空态非错误页；失败按错误码给文案 | 🔶 口径函数已有 `frontend/src/__tests__/contract.test.js`；页面级三态待组件测试 |
| T-FE-02 | 字段映射一致性 | 页面用到的每个字段能在 `backend/api-spec.md` 找到 | 🔶 `contract.test.js` 已钉模型清单/五维度分组；逐字段映射待补 |
| T-FE-03 | 错误码 → 文案分发 | 40001/40100/40400/50000 各得对应提示，50000 不回显堆栈 | 🔶 后端侧已断言不泄露（`test_security_boundaries.py`）；前端文案分发待组件测试 |

### 4.2 集成测试

| 编号 | 用例 | 期望 |
|---|---|---|
| T-IT-01 | 一条提交走完 列表→详情→趋势（真实库 + 真实模型） | 三页面数据同源，字段无漂移 |
| T-IT-02 | 预测后入库 → 列表可见 | `prediction` 表幂等 upsert，重复预测不产生重复行 |
| T-IT-03 | 趋势看板按周/月聚合 | 聚合口径与 `query-api` 规格一致 |

### 4.3 系统测试

| 编号 | 用例 | 期望 |
|---|---|---|
| T-ST-01 | 正向演示主链路（`repo/demo-script-sprint1.md` §2） | 列表→详情归因→趋势看板全通 |
| T-ST-02 | 无效 API Key → 401 | 页面提示重新登录，不给「重试」 |
| T-ST-03 | 非法 `commit_hash` → 404 | 页面展示空态而非崩溃 |
| T-ST-04 | 8 个 `model_name` 逐一查询 | 每个模型均有结果，无 500 |
| T-ST-05 | 回归：新增模型不破坏既有四接口 | 契约三口径不变 |

### 4.4 非功能测试

| 编号 | 用例 | 期望 | 依据 |
|---|---|---|---|
| T-NF-01 | 性能：`POST /api/predict` 循环 100 次 | p50/p95/p99 分位数，**95% < 500ms** | `backend/api-spec.md` §四 |
| T-NF-02 | 安全：缺令牌 + 畸形参数两组 | 不回显堆栈/SQL/路径 | `backend/api-spec.md` §四 |
| T-NF-03 | 可靠：空数据 / 断连重试 | 空态可恢复，重试有界 | `design/non-functional.md` |
| T-NF-04 | 易用：三态 + 阈值展示一致性 | 阈值只在 `frontend/pages.md` 一处定义 | `design/non-functional.md` |

## 5. 执行与报告

| 项 | 约定 |
|---|---|
| 后端单测 | `cd backend && python -m pytest -q` |
| 模型单测 | `cd data_model && python -m pytest -q`（`data_model/tests/` 已建，8 条；干净 clone 无 `.pkl` 时相关用例自动 skip） |
| 前端单测 | `cd frontend && npm run test:unit`（vitest 已入 `devDependencies` 并加 `test:unit` script；需先 `npm ci`） |
| 复现性 | `data_model` 各脚本照 `data-pipeline.md` 命令重跑，指标报告逐行一致（±0） |
| 报告 | 每 Sprint 末产出 `docs/common/test-report-<sprint>.md`：用例数 / 通过 / 失败 / 覆盖率 / 已知失败原因 |
| 覆盖率目标 | 后端行覆盖 Sprint 2 ≥60%、Sprint 3 ≥75%；模型线以**复现一致性（±0）**为主要验收 |

## 6. 缺陷与 evidence 归档

- 缺陷按 `repo/defect-management.md` 五项记录（现象 / 复现条件 / 优先级 / 处理状态 / 关联提交或 change）；测试发现的缺陷须带 `T-` 编号反查。
- evidence 按线归本包：`backend/evidence/`、`frontend/evidence/`、`model/evidence/`；录屏命名 `demo-sprint1-YYYYMMDD.mp4`。
- evidence 索引登记在对应 Sprint 的 `docs/common/test-report-<sprint>.md`，不另建第三份清单。

## 7. 退出准则（Sprint 3 验收前必须全满足）

1. 四层用例全部执行，失败项有 Issue 记录且状态明确（不接受「未跑」）。
2. 每个核心功能有 1 正向 + ≥1 异常的通过证据。
3. 至少 1 条端到端链路集成/系统测试通过并留录屏。
4. 至少 2 项非功能需求出验证证据（当前锁定性能 + 安全，可靠/易用补佐证）。
5. 缺陷处置记录可导出，五项字段齐全。
6. CI 门禁（`design/engineering.md` §3）跑通，单测随 PR 自动执行。

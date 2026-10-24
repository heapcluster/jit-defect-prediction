# 非功能需求（NFR）

> 课程：「非功能需求至少选择并落实 2 项与项目相关的质量需求（安全、性能、可靠性、易用性等）。」
> 本组落实 **4 项**，其中性能 + 安全为 Sprint 3 必须验证项（证据脚本见 `docs/backend/acceptance.md` B5/B6）。

## 1. 安全（P0，必须验证）

- 四个接口统一 `X-API-Key` 鉴权；缺失/不匹配 → 401（`code=40100`），不提示令牌哪一位错。
- 对外错误码只用契约 5 个；`50000` 不回显堆栈/SQL/文件 路径（课程「非法输入不泄露内部信息」）。
- 已接受的代价：固定令牌无过期/轮换、随前端产物下发（演示环境内网、数据不敏感）。
- **证据**：`backend/scripts/evidence/security-2026-10-24.md`（main `0773a49` 重跑：脚本 6/6 PASS、5 响应体 × 10 项泄露模式 0 命中、50000 掩码实测）+ 两张实拍截图 `security-shot1-missing-token.png`（缺令牌 401/40100/63 字节）、`security-shot2-bad-params.png`（`size=101` / `granularity=day` / 39 位哈希三例 400/40001）。截图为浏览器在被测服务自身 `/docs` 页的同源 `fetch` 实拍。旧两份 09-19/09-20 证据已标不可再引。

## 2. 性能（P0，必须验证）

- `POST /api/predict` 95% 请求 < 500ms（课程明确「对外提供在线预测服务」的压测靶子）。
- **证据**：`backend/scripts/` 压测脚本循环 100 次，输出 **p50/p95/p99** 分位数 + 截图。不得拿查询接口代替（查询读索引，快不代表模型推理性能）。
- **2026-10-24 实测结论（见 §5.2）**：默认路径（不传 `model_name` → 版本序最新 `xgb_v1`）p95=15.5ms **达标**；`lr_v1` p95=9.0ms 达标；**`rf_v1` p95=713.8ms 未达标**（D-14，待裁定）。旧证据 `perf-real-2026-09-20.md` 测的是 #97 之前的接口，不可再引。

## 3. 可靠性

- 预测幂等：同一 `(commit_hash, model_name)` 重复调用，库里只留最新一行（不累积重复）。
- 数据可复现：固定 `camel-4.23.0`，别人照命令跑出同一份统计（±0）。
- 时间序切分防泄漏：随机切分 = 缺陷。
- **证据落点**（2026-10-13 已从「由联调与演示佐证」改为**可点验的文件**）：
  - 契约一致性（14 项特征列名与顺序、交付清单 3 模型、`feature_version=v1`）→ `data_model/tests/test_feature_contract.py`（8 passed）；
  - 复现一致性（同一切分/特征/种子，指标报告逐行一致）→ `data_model/reports/model_matrix.md`「与 `model_metrics.md` 差异 0 项」；
  - 幂等与空数据不冒充 → `backend/tests/test_predict_api.py`、`test_commits_api.py`；
  - 灌库幂等（四类 CSV 各灌两遍行数不变）与「同哈希 POST 两次只留一行」→ 三端联调实测记录 `backend/scripts/evidence/integration-2026-10-24.md`（SQLite 全量库，见 §5.3）；MySQL 侧待隔离库授权后补。

## 4. 易用性

- 三态齐全：加载中 / 空数据（**不是错误**）/ 请求失败，文案与后续操作不同。
- 风险着色阈值只在 `docs/frontend/pages.md` 一处定义（`≥0.5`/`≥0.3`），三页统一；`high_risk_count` 用后端值不重算。
- 字段名前后端同源，不驼峰转换。
- **证据落点**（2026-10-24 订正：Sprint 1 时期引用的 `frontend/src/__tests__/contract.test.js` 从未合入 main，只在未合入的提交 `8cf3c78`；main 上前端单测为 `frontend/tests/` 两份）：
  - 阈值/百分比口径 → `frontend/tests/risk.spec.js`（4 条：≥0.5 高 / ≥0.3 中 / 其余常规 / 边界归上一档）；
  - 错误码 → 文案分发、50000 不回显服务端细节 → `frontend/tests/request.spec.js`（6 条，含 40001/40100/40400/50000 四档 `it.each`）；
  - 常量唯一来源 → `frontend/src/utils/risk.js`（阈值函数只此一处，页面不各自硬编码）；
  - 空数据/40400/50000 的页面表现口径 → `docs/frontend/pages.md` §5。
  - **仍缺**：三态（加载中 / 空数据 / 失败）的组件级用例与页面字段 → `api-spec.md` 的逐字段映射用例（T-FE-01/02，0 覆盖），见 `docs/common/test-report-sprint2.md` §2.4。易用性结论在补齐前只算「口径层已验证」。

## 验收（课程 ≥2 项验证）

性能 + 安全两项在 Sprint 3 出验证证据（在 `nfr-evidence-scripts` change 内）。可靠性/易用性**不再只靠「联调与演示佐证」**——已分别落到上表的测试文件与常量文件，Sprint 3 只需补压测分位数与两组安全截图即可闭环 4/4。

## 5. D2 验证结果（2026-10-24 实测）

> 本节是课程「≥2 项非功能需求出验证证据」的结论章，只写**已发生的测量**；每条结论都能点回 `backend/scripts/evidence/` 下的原始文件。测量环境统一：main `0773a49`、Python 3.12.7（仓库根 `.venv`）、fastapi 0.141.1 / uvicorn 0.53.0 / SQLAlchemy 2.0.54、真交付权重（`feature_order.txt` `[models]` = lr/rf/xgb，md5 与 2026-10-24 交付包一致）、真 uvicorn 进程（非 TestClient）。数据库为 **SQLite 隔离库**（本机 `jit` 账号无 `CREATE DATABASE` 权限，MySQL 侧待苏哲勋授权隔离库后补跑，补跑前本节数字不代表 MySQL）。

### 5.1 安全（T-NF-02）——结论：通过

- 脚本用例 6/6 PASS：缺令牌 401/40100、错令牌 401/40100、`size=101` 400/40001（message 指出 `size` 与上限 100）、`granularity=day` 400/40001、39 位哈希 400/40001、泄露扫描无命中。
- 泄露扫描 5 个响应体 × 10 项模式（`security_cases.py::LEAK_PATTERNS` 4 正则 + `test_security_boundaries.py` 6 关键字）= **50 次检查 0 命中**；响应体最长 93 字节，只有 `code` / `message` / `data` 三键。
- 50000 掩码实测：空 `MODEL_DIR` 起服务 → `POST /api/predict` 返回 `HTTP 500 code=50000 message=internal error`（53 字节），失败细节只进服务端日志。
- 两张实拍截图（浏览器同源 `fetch`，非 mock）：`security-shot1-missing-token.png`、`security-shot2-bad-params.png`。
- 单测层同源断言 50 条（`test_security_boundaries.py`）在 main 上全绿，见 `docs/common/test-report-sprint2.md` §2.2。
- 原始记录：`backend/scripts/evidence/security-2026-10-24.md`。

### 5.2 性能（T-NF-01）——结论：默认路径达标；`rf_v1` 未达标（D-14，待裁定）

分位数口径：升序第 `ceil(q*n)` 位（`perf_loop.py::percentile`，design D4），**不是平均值**；靶子 `POST /api/predict` 循环 100 次，不用查询接口代替。

| 测量 | 库 | p50 | p95 | p99 | max | p95<500ms |
|---|---|---|---|---|---|---|
| 默认路径·冷启动（服务刚起，第 1 个请求含 SHAP 解释器构造） | SQLite 全量库（84,461 提交 / 83,943 预测） | 10.1 | **11.3** | 12.4 | 664.1 | ✅ 达标 |
| 默认路径·预热（三端联调链内，解释器已构造） | SQLite 全量库 | 9.7 | **11.9** | 16.9 | 50.2 | ✅ 达标 |
| 单模型 `xgb_v1` | SQLite 种子库（3 行） | 13.3 | 15.5 | 16.9 | 832.5 | ✅ 达标 |
| 单模型 `lr_v1` | SQLite 种子库（3 行） | 7.7 | 9.0 | 9.5 | 776.9 | ✅ 达标 |
| 单模型 `rf_v1` | SQLite 种子库（3 行） | 653.0 | **713.8** | 751.0 | 1638.6 | ❌ **未达标** |

读法与边界：

- **max 一列不是失败项**：100 次里的最大值是**首个请求**的 SHAP 解释器惰性构造（`model_registry.get_explainer` 构造后缓存），其后 99 次不含该成本；判定只看 p95。
- **`rf_v1` 的未达标是契约级冲突，不是测量误差**：契约三 §4 把 `lr_v1/rf_v1/xgb_v1` 都列为可切换 `model_name`，而 §2 性能靶子对「`POST /api/predict`」只给一个 500ms。默认路径走 `xgb_v1` 所以演示与前端不受影响，但任何显式指定 `rf_v1` 的调用都超靶子 43%。已登记 `docs/repo/defect-records.md` **D-14**，三选一待蒋励 + 苏哲勋裁定：① 在线可切换范围收窄为 lr/xgb（动契约三枚举与 `specs/model-coverage` R6，须走 change）；② 靶子按模型分别定；③ 优化 rf 在线推理。本节不预判。
- 旁证链：2026-10-23 的函数级探测（`on-demand-commit-2026-10-23.md`，rf_v1 五次 605–947ms）当时已提示冲突；本轮把它升级成了真 HTTP + 真库 + 100 次的正式测量。
- 旧证据 `perf-real-2026-09-20.md`（p50 12.6 / p95 21.6 / p99 67）测的是 #97 之前的 `POST /api/predict`（不现算 14 维特征），**不可再引**；`perf-placeholder-2026-09-19.md` 是占位模型，同样不可再引。
- 原始记录：`backend/scripts/evidence/perf-2026-10-24.md`。

### 5.3 可靠性——佐证（非本轮新测，列可点验落点）

- 预测幂等：单测 `test_predict_api.py::test_predict_idempotent_single_row`；联调实测「同哈希 POST 两次、`prediction` 表该 `(commit_hash, model_name)` 键恰 1 行」见 `integration-2026-10-24.md`。
- 灌库幂等：单测 `test_ingest.py` + `test_integration_api.py`；联调实测四类 CSV 各灌两遍行数不变，见同上。
- 契约一致性：`data_model/tests/test_feature_contract.py`（14 项列名与顺序、交付清单 3 模型、`feature_version=v1`）。
- 复现一致性（±0）：模型线主验收口径，见 `data_model/pipelines/expert/reports/model_metrics.md` 与 `test-report-sprint2.md` §2.3。

### 5.4 易用性——佐证与缺口

- 已验证（口径层）：阈值单一来源与三档着色 → `frontend/tests/risk.spec.js` 4 条；错误码 → 文案、50000 不回显 → `frontend/tests/request.spec.js` 6 条；均在 main 上实跑通过（`test-report-sprint2.md` §2.4）。
- **缺口（如实标注）**：三态（加载中 / 空数据 / 失败）的组件级用例与页面字段 → 契约逐字段映射用例为 **0 覆盖**（T-FE-01/02；Sprint 1 报告引用的 `contract.test.js` 从未进 main）。在补齐前，易用性只算「口径层已验证、页面层未验证」。

### 5.5 未闭环项（不藏）

| # | 项 | 状态 | 阻塞 |
|---|---|---|---|
| 1 | MySQL 侧复跑（建库 / 灌库 / 压测） | 待授权 | `jit` 账号无 `CREATE DATABASE`；需苏哲勋建隔离空库 |
| 2 | `rf_v1` 超靶子的处置 | 待裁定 | D-14，三选一须走 change |
| 3 | T-FE-01/02 组件级用例 | 待补 | 前端线（刘帅华） |
| 4 | 系统层录屏（T-ST-01~05） | 待联调后 | 依赖三端联调与演示排期 |

## 1. 契约与裁定回填（跨线）

- [x] 1.1 逐字段核对 `docs/pages.md` 第 2–4 节字段清单与 `api-format.md` 1.4 响应，产出「页面要用但接口没有」的缺口清单，以 Issue 形式交付刘帅华
      —— 2026-09-18 完成：核对零缺口；交付单为 Issue #31（指派 1lsh74269，含逐字段结论），待其确认后关闭
      —— 跨线交付：前端线，形式为 GitHub Issue（含逐字段对照表）
- [x] 1.2 PR #6 合入后，按合入版文件头（契约一 1.4 / 契约二 1.2 / 契约三 1.3）核对本 change 规格逐条一致（四张表、X-API-Key、predict、SHAP），并把本 change 内全部契约版本引用同步为该组版本号；不一致处以 change 更新修正本侧规格
      —— 2026-09-18 完成：#6 合入为 ad8277e；核对一致、引用已于同步提交改齐，writing-norms §3.3 的 git grep 命令自扫无残留
      —— 跨线交付：核对结论交付契约线（蒋励统稿），形式为 PR #6 评审意见或契约变更 Issue；本侧规格与引用修正以本 change 的更新提交交付（后端线，随本 PR）
- [x] 1.3 「提交存在但无预测记录」的响应形态（design D3）在 PR #6 评审意见提出补记进契约三；若已冻结则走契约变更流程
      —— 完成：契约三 1.3（d3a1327）§2 已补 null 口径与「不得 40400 / 不得 0.0 冒充」，§3 阈值定死为服务端常量 0.5；变更日志署名「后端线吕建江提出」；9/19 提前冻结宣布（PR #40，原计划 9/23）
      —— 跨线交付：契约线（定稿人吕建江、冻结人蒋励），形式为 PR #6 评审意见；冻结后则走契约变更 PR
- [x] 1.4 「commit_feature 无行 → features null、code=0」补记进契约三 §2（与 pages.md 同口径；PR #30 审 7），并入 9/23 冻结宣布 PR
      —— 2026-09-19 完成：契约三 1.4 §2 与冻结结论表已补记（冻结 PR 提前冻结，不再等 9/23）

## 2. 依赖与环境

- [x] 2.1 `backend/requirements.txt` 新增 `scikit-learn` / `xgboost` / `shap` / `numpy`（依据：裁定 A+C 与契约三冻结结论的 SHAP）；安装跑通后按文件头约定回填 `==x.y.z`
      —— 版本已钉 ==x.y.z 并安装跑通（pytest 33/33）
- [x] 2.2 `.env.example` 入库：`DATABASE_URL` / `API_TOKEN` / `MODEL_DIR` 全键名、不含真实值；`git status --short` 中不出现 `.env`

## 3. 库表与灌入

- [x] 3.1 四张表（`commit` / `commit_label` / `commit_feature` / `prediction`）的 SQLAlchemy 模型，逐字段对照契约一 1.4 表一/二/三与契约二 §2/§3，列出缺列/改名/自造列并闭环
- [x] 3.2 `prediction` 表加 `(commit_hash, model_name)` 唯一索引（predict 幂等落库与方案 C 灌入共用键，design D7/D4；契约一允许的后端自属冗余索引）
- [x] 3.3 索引自检：实测 `commit_hash` 唯一索引拒重复插入、`committed_at` 普通索引存在（`SHOW INDEX` 输出留证）
- [x] 3.4 建库入口 `python -m app.db init`（design D1），满足「干净 clone 后一条命令建好库」；命令与「灌入需先跑数据线 01–04」的前提写进 `backend/README.md`
      —— README「建库与灌入」小节同提交补齐（15e052c）
- [x] 3.5 灌入脚本 `python -m app.ingest <commits|labels|features|predictions> <csv>`：幂等键按 design D4；缺主键字段的行失败并报行号、整批回滚
- [x] 3.6 种子数据脚本（小体量、命名带 seed，仅供联调与测试；只进本地库，不入库）

## 4. 接口

- [x] 4.1 包络与错误码中间件：只用 0/40001/40100/40400/50000；`50000` message 固定文案，细节（含模型文件路径）只写服务端日志
- [x] 4.2 鉴权依赖：请求头 `X-API-Key`，缺失或不匹配返回 40100（HTTP 401）、message 固定 `missing or invalid token`；四个接口一律适用
- [x] 4.3 `GET /api/commits`：`risk_score` 降序、分页默认 20 上限 100、`min_risk`/`model_name`/时间范围筛选
- [x] 4.4 `GET /api/commits/{commit_hash}`：元信息 + 14 项特征值（读 `commit_feature`，键名逐字同契约二）+ `explanation`；无预测记录形态按 design D3
- [x] 4.5 `GET /api/trends`：week/month 聚合、`high_risk_count` 后端按**固定常量 0.5** 计算（不开放参数，design D10）、`series` 单模型一组；`start_time`/`end_time`/`model_name` 参数与缺省口径照契约三 §3 与本 change 规格
- [x] 4.6 输入校验：`size`/`page`/`min_risk`/`granularity`/时间格式的类型、越界与枚举校验，违例 40001 且 message 指出参数名
- [x] 4.7 模型加载器（design D6）：启动时加载 `MODEL_DIR` 下 `.pkl`，注册表与「默认最新」口径；加载失败不阻断启动、predict 时返回 50000 且不回显路径
- [x] 4.8 `POST /api/predict`：`commit_hash` 必填且 40 位十六进制（违例 40001）；不在 `commit` 表 40400 `commit not found`；无特征行 40400 `features not found for this commit`；实时推理（MUST NOT 查 `prediction` 表代替）；结果按 `(commit_hash, model_name)` 幂等落库、只留最新一行，`feature_version` 读自 `commit_feature` 同值写入（design D7）
- [x] 4.9 SHAP 解释（design D8）：`explanation` 逐特征含 `contribution` 与 `direction`，键名与 `features` 同一套
- [x] 4.10 苏哲勋 #30 首审修复全项：INDEX_ASSERTIONS 驱动索引自检（含 prediction 两条）、默认模型统一版本序且详情与列表同源、explainer 惰性缓存、并发双插回落 update、分页下推 COUNT/LIMIT、lifespan 替换 on_event
      —— 证据：本提交；pytest 34/34 绿（新增版本序默认模型用例）、ruff 全清、validate --strict 通过

## 5. 镜像比对与测试

- [x] 5.1 导出 FastAPI `openapi.json`，与契约三 1.4 四个接口逐字段比对，列出偏离并闭环 —— **改代码不改契约**
      —— test_mirror.py 8 条字段级镜像断言 + openapi-export.json 存档
- [x] 5.2 `backend/tests/` 覆盖：五个错误码各至少一例；边界 `size=100/101`、空数据、哈希不存在、哈希非 40 位、特征行缺失、模型文件缺失、predict 重复调用只留一行
- [x] 5.3 MySQL 8 真库自检一轮（建库 + 灌入 + 四接口冒烟）；凭据不可用时以 SQLite 内存库证据先行并登记待补
      —— 2026-09-18 完成：专建账号 jit 真库自检全绿（索引证据、灌入幂等、401/50000 掩码冒烟），证据存档仓库外 evidence-5.3-mysql.md；顺带发现并修复 SessionLocal 无 bind 缺陷（799745e）
- [x] 5.4 验证证据：命令与关键输出贴进 PR 描述（DoD 第 2 条）
      —— 已由 PR #30 描述「怎么验证」一节交付：pytest 34/34、ruff 全清、openapi 字段级镜像断言 8 条、SQLite 与 MySQL 真库各一轮自检

## 6. 交付

- [x] 6.1 提案（本 change 的 proposal/specs/design/tasks）自 `docs/spec/backend-db-and-query-api` 提 PR 至 `main`，描述写清四件事并关联本 change id；审阅人苏哲勋
      —— **PR #27 已合入**（2026-09-18 06:01，审阅人苏哲勋）；先例：PR #1 与 `docs/spec/model-training-delivery` 均按「提案先合、实现后跟」走
- [x] 6.2 提案合入后自 `main` 切实现分支 `feat/backend/db-and-query-api`，按任务 2–5 实现并提第二个 PR；审阅人苏哲勋
      —— **PR #30 已合入**（2026-09-19 10:13，审阅人苏哲勋）；实现阶段 2–5 组的勾选与证据已在 #30 内回填
- [x] 6.3 回飞书看板更新任务 7 状态与关联链接；两个 PR 合入后各自删除分支（`docs/collaboration.md` §1.6）
      —— 看板「7 数据库表结构与接口格式」行已于 2026-09-20 更新为 **已完成** 并补关联链接（PR #30）；两个源分支随合并按任务 2 的「自动删除源分支」设置清掉

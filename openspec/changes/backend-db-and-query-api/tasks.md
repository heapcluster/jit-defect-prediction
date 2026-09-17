## 1. 契约与裁定回填（跨线）

- [ ] 1.1 逐字段核对 `docs/pages.md` 第 2–4 节字段清单与 `api-format.md` v1.2 响应，产出「页面要用但接口没有」的缺口清单，以 Issue 形式交付刘帅华
      —— 跨线交付：前端线，形式为 GitHub Issue（含逐字段对照表）
- [ ] 1.2 核对 PR #6（`docs/docs/freeze-contracts-v1`）合入后的契约一 v1.2 / 契约三 v1.2 与本 change 规格逐条一致（四张表、X-API-Key、predict、SHAP）；不一致处以 change 更新修正本侧规格
- [ ] 1.3 「提交存在但无预测记录」的响应形态（design D3）在 PR #6 评审意见提出补记进契约三；若已冻结则走契约变更流程
      —— 同条评审意见一并提议修订契约三第 4 节幂等句：由「库里只保留最新一行」改为「不写库、不改状态」（2026-09-17 聊天裁定，design D7）
      —— 截止 9/23 冻结宣布前

## 2. 依赖与环境

- [ ] 2.1 `backend/requirements.txt` 新增 `scikit-learn` / `xgboost` / `shap` / `numpy`（依据：裁定 A+C 与契约三冻结结论的 SHAP）；安装跑通后按文件头约定回填 `==x.y.z`
- [ ] 2.2 `.env.example` 入库：`DATABASE_URL` / `API_TOKEN` / `MODEL_DIR` 全键名、不含真实值；`git status --short` 中不出现 `.env`

## 3. 库表与灌入

- [ ] 3.1 四张表（`commit` / `commit_label` / `commit_feature` / `prediction`）的 SQLAlchemy 模型，逐字段对照契约一 v1.2 表一/二/三与契约二 §2/§3，列出缺列/改名/自造列并闭环
- [ ] 3.2 `prediction` 表加 `(commit_hash, model_name)` 唯一索引（方案 C 灌入幂等键，design D4；与 predict 无关 —— predict 不写库，见 D7）
- [ ] 3.3 索引自检：实测 `commit_hash` 唯一索引拒重复插入、`committed_at` 普通索引存在（`SHOW INDEX` 输出留证）
- [ ] 3.4 建库入口 `python -m app.db init`（design D1），满足「干净 clone 后一条命令建好库」；命令与「灌入需先跑数据线 01–04」的前提写进 `backend/README.md`
- [ ] 3.5 灌入脚本 `python -m app.ingest <commits|labels|features|predictions> <csv>`：幂等键按 design D4；缺主键字段的行失败并报行号、整批回滚
- [ ] 3.6 种子数据脚本（小体量、命名带 seed，仅供联调与测试；只进本地库，不入库）

## 4. 接口

- [ ] 4.1 包络与错误码中间件：只用 0/40001/40100/40400/50000；`50000` message 固定文案，细节（含模型文件路径）只写服务端日志
- [ ] 4.2 鉴权依赖：请求头 `X-API-Key`，缺失或不匹配返回 40100（HTTP 401）、message 固定 `missing or invalid token`；四个接口一律适用
- [ ] 4.3 `GET /api/commits`：`risk_score` 降序、分页默认 20 上限 100、`min_risk`/`model_name`/时间范围筛选
- [ ] 4.4 `GET /api/commits/{commit_hash}`：元信息 + 14 项特征值（读 `commit_feature`，键名逐字同契约二）+ `explanation`；无预测记录形态按 design D3
- [ ] 4.5 `GET /api/trends`：week/month 聚合、`high_risk_count` 后端按阈值 0.5 计算、`series` 单模型一组
- [ ] 4.6 输入校验：`size`/`page`/`min_risk`/`granularity`/时间格式的类型、越界与枚举校验，违例 40001 且 message 指出参数名
- [ ] 4.7 模型加载器（design D6）：启动时加载 `MODEL_DIR` 下 `.pkl`，注册表与「默认最新」口径；加载失败不阻断启动、predict 时返回 50000 且不回显路径
- [ ] 4.8 `POST /api/predict`：`commit_hash` 必填且 40 位十六进制（违例 40001）；不在 `commit` 表 40400 `commit not found`；无特征行 40400 `features not found for this commit`；实时推理（MUST NOT 查 `prediction` 表代替）；**无状态：不写库、不改状态**（裁定口径，design D7）
- [ ] 4.9 SHAP 解释（design D8）：`explanation` 逐特征含 `contribution` 与 `direction`，键名与 `features` 同一套

## 5. 镜像比对与测试

- [ ] 5.1 导出 FastAPI `openapi.json`，与契约三 v1.2 四个接口逐字段比对，列出偏离并闭环 —— **改代码不改契约**
- [ ] 5.2 `backend/tests/` 覆盖：五个错误码各至少一例；边界 `size=100/101`、空数据、哈希不存在、哈希非 40 位、特征行缺失、模型文件缺失、predict 重复调用不写行
- [ ] 5.3 MySQL 8 真库自检一轮（建库 + 灌入 + 四接口冒烟）；凭据不可用时以 SQLite 内存库证据先行并登记待补
- [ ] 5.4 验证证据：命令与关键输出贴进 PR 描述（DoD 第 2 条）

## 6. 交付

- [ ] 6.1 提案（本 change 的 proposal/specs/design/tasks）自 `docs/spec/backend-db-and-query-api` 提 PR 至 `main`，描述写清四件事并关联本 change id；审阅人苏哲勋
      —— 先例：PR #1 与 `docs/spec/model-training-delivery` 均按「提案先合、实现后跟」走
- [ ] 6.2 提案合入后自 `main` 切实现分支 `feat/backend/db-and-query-api`，按任务 2–5 实现并提第二个 PR；审阅人苏哲勋
- [ ] 6.3 回飞书看板更新任务 7 状态与关联链接；两个 PR 合入后各自删除分支（`docs/collaboration.md` §1.6）

## 1. 契约定稿与冻结（截止 9/23，跨线）

- [ ] 1.1 逐字段核对 `docs/pages.md` 第 2–4 节字段清单与 `api-format.md` 三个接口响应，产出「页面要用但接口没有」的缺口清单，以 Issue 形式交付刘帅华
      —— 跨线交付：前端线，形式为 GitHub Issue（含逐字段对照表）
- [ ] 1.2 裁定鉴权方式（建议固定共享令牌，design D2），回填 `api-format.md` 待确认第 2 条
- [ ] 1.3 与组内结清本提案待决问题 1 与 3（`commit_feature` 是否建表、无预测记录的响应形态），回填对应契约
- [ ] 1.4 收刘帅华对三项待确认（按作者/子系统分组、多模型对比、模型下拉来源）的反馈并回填 `api-format.md`；文件头改「已冻结 + 日期」，提冻结 PR
      —— 截止 9/23；届时未收到反馈则升级蒋励在周会裁定，**不带着假设冻结**

## 2. 库表

- [ ] 2.1 写三张表（`commit` / `commit_label` / `prediction`）的 SQLAlchemy 模型，逐字段对照 `data-fields.md` 表一/二/三，列出缺列/改名/自造列并闭环
- [ ] 2.2 索引自检：实测 `commit_hash` 唯一索引能拒重复插入、`committed_at` 普通索引存在（`SHOW INDEX` 输出留作证据）
- [ ] 2.3 建库入口 `python -m app.db init`（design D1），满足「干净 clone 后一条命令建好库」；命令写进 `backend/README.md`
- [ ] 2.4 `commit_feature` 建表与特征 CSV 灌入 —— 前置：待决问题 1 裁定为建表；否则以 change 更新删除本条
- [ ] 2.5 `.env.example` 入库（列全键名、不含真实值）；`git status --short` 中不出现 `.env`

## 3. 查询接口

- [ ] 3.1 包络与错误码中间件：只用 0/40001/40100/40400/50000 五个码；`50000` 的 message 固定文案，细节写服务端日志
- [ ] 3.2 鉴权依赖：缺失/非法令牌返回 40100（HTTP 401）
- [ ] 3.3 `GET /api/commits`：`risk_score` 降序、分页默认 20 上限 100、`min_risk`/`model_name`/时间范围筛选
- [ ] 3.4 `GET /api/commits/{commit_hash}`：元信息 + 14 项特征值（键名逐字同契约二）+ `explanation`；无预测记录的形态按 design D3
- [ ] 3.5 `GET /api/trends`：week/month 聚合、`high_risk_count` 由后端按阈值 0.5 计算、`period` 格式照契约
- [ ] 3.6 输入校验：`size`/`page`/`min_risk`/`granularity`/时间格式的类型、越界与枚举校验，违例返回 40001 且 message 指出参数名

## 4. 灌入与种子数据

- [ ] 4.1 `prediction_result.csv` 灌入脚本（裁定 C）：按 `(commit_hash, model_name, feature_version)` 幂等，重跑不产生重复行；缺 `commit_hash` 的行失败并报行号、整批回滚
      —— 字段映射以上游 change `model-training-and-delivery` 合入 `main` 的版本为准
- [ ] 4.2 种子数据脚本（小体量、命名带 seed，仅供联调与测试；数据只进本地库，不入库）

## 5. 镜像比对与测试

- [ ] 5.1 导出 FastAPI `openapi.json`，与 `api-format.md` 三个接口逐字段比对，列出偏离并闭环 —— **改代码不改契约**
- [ ] 5.2 `backend/tests/` 覆盖：五个错误码各至少一例；边界 `size=100/101`、空数据、哈希不存在、无令牌
- [ ] 5.3 验证证据：命令与关键输出贴进 PR 描述（DoD 第 2 条）

## 6. 交付

- [ ] 6.1 提案（本 change 的 proposal/specs/design/tasks）自 `docs/spec/backend-db-and-query-api` 提 PR 至 `main`，描述写清四件事并关联本 change id；审阅人苏哲勋
      —— 先例：PR #1 与 `docs/spec/model-training-delivery` 均按「提案先合、实现后跟」走
- [ ] 6.2 提案合入后自 `main` 切实现分支 `feat/backend/db-and-query-api`，按任务 2–5 实现并提第二个 PR；审阅人苏哲勋
- [ ] 6.3 回飞书看板更新任务 7 状态与关联链接；两个 PR 合入后各自删除分支（`docs/collaboration.md` §1.6）

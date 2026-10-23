## Context

基线为 main `f5ca61d`。`backend/app/api/commits.py:45-47` 的 `_check_hash()` 用 `commit_hash.lower()` 判定字符集后返回 `None`；`commit_detail()`（120-153 行）随后拿**原样入参**查 `commit`、`commit_feature` 与两处 `prediction`。`backend/app/api/predict.py:32-36` 则是先 `commit_hash = body.commit_hash.lower()` 再查库、落库、回显。缺陷 D-09 在 `docs/repo/defect-records.md` §2 登记为 P3，`backend/tests/test_security_boundaries.py:124` 用测试钉住了旧行为，其 docstring 明确写「修复走 OpenSpec change：在查询前统一 `lower()`，或在校验阶段直接归一化」。本设计取后者。

## Goals / Non-Goals

**Goals:** 同一个 40 位十六进制哈希（任意大小写）在 GET 详情与 POST 预测上表现一致；归一化只在一处发生；钉住旧行为的测试转成钉住新行为。

**Non-Goals:** 不统一两处校验实现（`predict.py` 的内联校验原样保留）；不改数据库列的 collation、不建函数索引；不改契约字段名、错误码与响应包络；不做 MySQL 实机验证（沿用现有 SQLite 夹具）。

## Decisions

- D1：归一化点放在 `_check_hash()`，签名由 `-> None` 改为 `-> str`，调用方必须使用返回值。理由：校验与归一化同一处，杜绝「校验放行、查询漏归一」再次分家；比在四个查询点各写一次 `.lower()` 更难漏。
- D2：不改数据库 collation，也不加函数索引，只在应用层归一化。方言差异必须写明：MySQL 8 默认排序规则 `utf8mb4_0900_ai_ci` 对大小写不敏感，因此这个缺陷在 MySQL 上可能复现不到；SQLite 的 `=` 对 TEXT 大小写敏感，本仓库的测试夹具与任何二进制/大小写敏感 collation 下必现。选应用层归一化的理由是跨方言一致、可测、不依赖建库参数。
- D3：响应 `data.commit_hash` 仍取库内值（小写），不回显请求原文。与 `POST /api/predict` 现状一致；前端拿到的哈希可直接用于后续请求，不会把大写形式再传回来造成二次困惑。
- D4：`predict.py` 的内联校验不重构（AGENTS.md 第五节「让你修一个缺陷，不要附带调整代码风格」），只加一条大小写幂等回归测试，锁住「POST 大写与小写写同一行 `prediction`」这条既有行为，防止将来有人把 predict 的归一化删掉后两条路径再次分家。
- D5：`docs/repo/defect-records.md` 的 D-09 行迁到 §1 已闭环，关联本 change 与 PR，证据列写测试路径 —— 缺陷记录规则要求「无证据不登记」，同理无证据不闭环。

## Risks / Trade-offs

- 复审者在 MySQL 上可能复现不到 → PR 描述与 tasks §5 都写明方言差异，权威复现路径是 SQLite 夹具测试（`cd backend && python -m pytest`）。
- 归一化改变「什么算同一个提交」→ 只影响大小写变体。Git 哈希本身是小写十六进制，`ingest` 写入的也是小写，库内不会存在大小写混存的同义哈希；新增测试覆盖混合大小写命中同一行。
- `_check_hash()` 返回值语义变化，未来新增调用方若忽略返回值就退回旧缺陷 → docstring 写明必须使用返回值，且 `commit_detail()` 的四处查询统一走同一个局部变量。

## Migration Plan

无数据迁移、无部署动作。单 PR 交付：代码 + 测试 + 缺陷记录 + 规格 delta。回滚只回退该 PR 的提交，库内数据不受影响（本 change 不写库）。

## Open Questions

1. `docs/backend/api-spec.md`（已冻结 v1.5）第 2 节是否补一句「`commit_hash` 大小写不敏感；响应回显库内小写值」？本 change 不自行改冻结契约，请 PO/SM 裁定。若裁定要补，我在同一 PR 内加这一行并按仓库惯例处理契约版本记号；若裁定不补，规格口径以 `openspec/specs/query-api/spec.md`（本 change 归档后）为准。

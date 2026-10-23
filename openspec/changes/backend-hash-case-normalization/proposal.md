## Why

`docs/repo/defect-records.md` §2 的 D-09（2026-10-13 登记，P3）至今未修：`backend/app/api/commits.py` 的 `_check_hash()` 用 `commit_hash.lower()` 判定十六进制，因此 40 位**大写**哈希能通过校验；但 `commit_detail()` 随后拿**原样字符串**去查 `commit` / `commit_feature` / `prediction`（库内哈希是小写），查不到就返回 `40400 commit not found` —— 对评审员是误导性提示（提交明明存在）。

同一个大写哈希在 `POST /api/predict` 上已经是正常的：`backend/app/api/predict.py` 第 36 行先 `commit_hash = body.commit_hash.lower()` 再查库、再写 `prediction`、并以归一化值回显。于是当前两条路径对同一输入不一致：**POST 能预测并落库，GET 详情却说该提交不存在**。D-09 的处理方式在登记时就写明「查询前统一 `lower()`，或在校验阶段直接归一化」，本 change 按后者落地。

## What Changes

- `_check_hash()` 由「只校验、返回 `None`」改为「校验并返回归一化后的小写哈希」；`commit_detail()` 用返回值查三张表（`commit` / `commit_feature` / `prediction` 两处），不再用原始入参。
- 校验语义不变：非 40 位、含非十六进制字符（大小写形式都算）仍返回 `40001`；归一化只是把已放行的输入映射到库内表示，不放宽任何拒收条件。
- 响应体不变：`data.commit_hash` 仍取库内 `commit.commit_hash`（小写），与 `POST /api/predict` 现有回显口径一致；不改字段名、不改错误码、不改包络。
- 改写钉住旧行为的测试 `backend/tests/test_security_boundaries.py::test_detail_uppercase_hash_passes_validation_but_not_found`（该测试的存在理由就是「修复走 OpenSpec change」），并补：大小写混合命中同一提交、库内不存在的大写哈希仍 `40400`、非十六进制仍 `40001`、POST 大小写两次调用只留一行 `prediction`。
- `docs/repo/defect-records.md` 的 D-09 行从「🔶 新登记，待 OpenSpec change」移到 §1 已闭环，关联本 change 与 PR，证据列指向新测试。
- 不做：不重构 `predict.py` 里重复的内联校验（避免把缺陷修复扩成重构）、不改数据库列或排序规则、不改契约字段名与错误码、不动前端、不做 MySQL 实机验证（沿用现有 SQLite 夹具）。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `query-api`：「提交详情查询」requirement 补一条哈希大小写归一化语义，并新增两个 Scenario（大写/混合大小写命中、归一化后仍不存在时 `40400`）。既有 Scenario 原文不改。

## Impact

- 代码：`backend/app/api/commits.py`（`_check_hash` 与 `commit_detail`，同一文件两处）。
- 测试：`backend/tests/test_security_boundaries.py`（改写 1 条 + 新增断言）、`backend/tests/test_predict_api.py`（补大小写幂等回归）。
- 规格：`openspec/changes/backend-hash-case-normalization/specs/query-api/spec.md`（归档后并入 `openspec/specs/query-api/spec.md`）。
- 缺陷记录：`docs/repo/defect-records.md` D-09 行。
- 契约文档：`docs/backend/api-spec.md` 已冻结（v1.5），本 change 不自行改它；是否需要补一句大小写口径由 PO/SM 裁定，见 `design.md` Open Questions。
- 依赖：无新增；环境仍以 `data_model/environment.yml` 为准。

# single-commit-feature-extraction — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/single-commit-features/spec.md`
> 负责人：model 苏哲勋（联调入口；模型线蒋励需复核 v1 口径）｜ 创建：2026-10-23 ｜ 状态：进行中（单条入口已验证，待模型线复核和后端接入）
> 关联需求：在线预测服务新提交现算特征；不扩大 14 项特征与当前八模型交付边界
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 单条入口（模型线）

- [x] 1.1 复用批量算法计算单条 14 项 v1 特征 — `data_model/preparation/03_extract_features.py` 的 `extract_single_commit()` 与 `--commit`，运行 `python data_model/preparation/03_extract_features.py --repo <本地仓库> --commit <40位哈希>` 输出一行 JSON。
- [x] 1.2 对照批量口径并验证失败路径 — `data_model/tests/test_single_commit_features.py`，运行 `python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q` 得到 3 passed。

## 2. 跨线交付（后端线）

- [ ] 2.1 将入口与字段顺序交付给 backend 吕建江 — `data_model/preparation/03_extract_features.py` 的 `extract_single_commit(repo_dir, commit_hash)` 返回值；后端在独立 PR 中接入 `POST /api/predict`，不得直接把全量扫描放进请求路径；以真实 Camel 仓库压测并归档证据。

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 单条抽取与批量逐项一致、CLI JSON、非法/不可达哈希 |
| 测试文件 | `data_model/tests/test_single_commit_features.py` |
| 用例数与结果 | 3 passed |
| 复现命令 | `python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q` |
| 正向用例 | 临时 Git 仓库三条提交 → 单条值与批量值逐项相等，列序相同 |
| 异常 / 边界用例 | 非 40 位、不可达哈希 → `ValueError`，不伪造向量 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 临时 Git 仓库 → 提交元信息 → 历史索引 → 14 项 v1 值 → CLI JSON |
| 测试文件 | `data_model/tests/test_single_commit_features.py` |
| 用例数与结果 | CLI 用例 1 passed；后端 HTTP 集成尚未执行 |
| 复现命令 | `python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q` |
| 关键断言 | 无 `commits.csv` 仍产出 JSON；不写批量 CSV；列序等于 `FEATURE_FIELDS` |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/single-commit-features/spec.md` 两个 Scenario |
| 用例数与结果 | 合成仓库 2 个场景通过；真实 Camel 交付验收未执行 |
| 复现命令 / 步骤 | `python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q`；`openspec validate single-commit-feature-extraction --strict --no-interactive` |
| 证据归档 | `data_model/preparation/reports/single_commit_validation.md` |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是，未达验收 | 当前全量扫描无真实 Camel p95 证据；`data_model/preparation/reports/single_commit_validation.md` 如实记录 |
| 安全 | 是 | 非法哈希拒绝；`python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q` |
| 可靠 | 是 | 与批量逐项一致、无 CSV 副作用；同上 |
| 易用 | 否 | 本 change 不涉及前端；`python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q` 仅验证模型入口 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 后端尚未接入新提交现算 | 本 change 只交付模型入口；HTTP 契约原写无特征行 40400 | backend 吕建江 / PO 苏哲勋 | 下一独立 PR，接入前先更新 `docs/api/predict.md` |
| 真实 Camel 历史扫描与在线 p95 未验证 | 本机无可用 Camel 全量仓库；全量扫描不宜直接进请求路径 | model 蒋励 / backend 吕建江 | 后端接入 PR 中预热或缓存并压测 |
| 八模型权重与数据不在干净 clone | 权重和 CSV 按仓库规则不入库 | model 蒋励 | 联调交付时提供受控投放与校验记录 |

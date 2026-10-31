# on-demand-commit-prediction — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/predict-api/spec.md`、`specs/query-api/spec.md`
> 负责人：backend 吕建江（PO 苏哲勋联调把关）｜ 创建：2026-10-23 ｜ 状态：进行中（合成联调通过，真实环境待验收）
> 关联需求：新提交现算 14 维特征并通过现行八模型交付清单在线预测
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 接口接入

- [x] 1.1 从服务端 `SOURCE_REPO` 读取新提交并落两表 — `backend/app/feature_source.py`、`backend/app/api/predict.py`；`cd backend && python -m pytest -o addopts='' -q tests/test_predict_api.py` 验证 200 与行数。
- [x] 1.2 新提交重复预测幂等且详情可见 — `backend/app/api/commits.py`、`backend/tests/test_predict_api.py`；同一命令断言每键一行、详情有风险值。
- [x] 1.3 处理非法/缺失来源与哈希规范化 — `backend/tests/test_predict_api.py`；同一命令断言固定 50000 不泄露路径、40 位格式校验与大小写一致。

## 2. 跨线真实交付

- [ ] 2.1 模型线蒋励将 Camel Git 副本与现行清单内八模型权重交付 backend 吕建江 — 交付清单在 `data_model/pipelines/expert/models/feature_order.txt`；后端按 `docs/api/predict.md` 对新 hash 完成真实 HTTP 演示并存证；受控权重与数据不入库。
- [ ] 2.2 以真实 Camel 新提交和当前八模型逐项做 100 次 p95、启动/首次请求耗时验证 — 结果存入本 change 的 `evidence/` 并在 PR 中链接；未达 500ms 时按提案记录与调整，不静默降级。

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 来源仓库读取、现算落库、幂等、大小写、错误码、详情回退 |
| 测试文件 | `backend/tests/test_predict_api.py` |
| 用例数与结果 | 后端全套 103 passed；真实 Camel 未测 |
| 复现命令 | `cd backend && python -m pytest -o addopts='' -q` |
| 正向用例 | 临时 Git 新提交 → 14 项特征、概率、三表落库、重复请求一行 |
| 异常 / 边界用例 | 来源目录不存在 → 50000 固定文案，不含服务端路径 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 模型线单条 v1 入口 → 后端两表 → 预测 → 详情及列表 |
| 测试文件 | `data_model/tests/test_single_commit_features.py`、`backend/tests/test_predict_api.py` |
| 用例数与结果 | 合成仓库链路通过；真实数据与 MySQL 未执行 |
| 复现命令 | `python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q`；`cd backend && python -m pytest -o addopts='' -q` |
| 关键断言 | 14 项列序相同、重复不增行、详情不因全局默认模型不同而显示 null |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/predict-api/spec.md`、`specs/query-api/spec.md` 的新增场景 |
| 用例数与结果 | 合成场景通过；真实 Camel 八模型/浏览器联调待验收 |
| 复现命令 / 步骤 | `cd backend && python -m pytest -o addopts='' -q`；`openspec validate on-demand-commit-prediction --strict --no-interactive` |
| 证据归档 | 旧证据已随 #187 删除；需在本 change 新建当前提交的可复核证据 |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是，尚未验收 | 真实 Camel 首次请求及 100 次 p95 缺失；需新证据 |
| 安全 | 是 | 来源路径仅服务端环境配置、50000 不回显路径；`cd backend && python -m pytest -o addopts='' -q tests/test_predict_api.py` |
| 可靠 | 是 | 同键幂等、异常来源拒绝、列序来自模型线；同上 |
| 易用 | 间接触及 | 详情回退有自动测试；浏览器三页截图待后续联调 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| Camel 完整历史、副本 HEAD 及 CSV 不在当前工作环境 | 原始数据和模型权重按规则不入库，需队友交付 | model 蒋励 / backend 吕建江 | 联调交付时 |
| 首次新提交全量历史扫描可能超过 500ms | 模型线单条入口复用批量算法，尚无索引预热或缓存 | model 蒋励 / backend 吕建江 | 真实 Camel 100 次压测后优化 |
| 随机森林 SHAP p95 旧报告高于 500ms | 现行八模型交付仍包含 rf；不能用夹具测试冒充性能验收 | model 蒋励 / backend 吕建江 | 真实权重压测并记录取舍 |
| 前端三页真实走查与截图缺失 | 当前只测 HTTP 合成链路 | frontend 刘帅华 / PO 苏哲勋 | 三线部署后 |

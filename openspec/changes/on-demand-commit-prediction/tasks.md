# on-demand-commit-prediction — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/predict-api/spec.md`、`specs/query-api/spec.md`
> 负责人：backend 吕建江（PO 苏哲勋联调把关）｜ 创建：2026-10-23
> 关联需求：新提交现算 14 维特征并通过已加载模型在线预测
> 状态：进行中（合成联调通过，真实环境待验收）

## 1. 接口接入

- [x] 1.1 从服务端 `SOURCE_REPO` 读取新提交并落两表 — `backend/app/feature_source.py`、`backend/app/api/predict.py`；`cd backend && python -m pytest -o addopts='' -q tests/test_predict_api.py` 验证 200 与行数。
- [x] 1.2 新提交重复预测幂等且详情可见 — `backend/app/api/commits.py`、`backend/tests/test_predict_api.py`；同一命令断言每键一行、详情显式传所选 `model_name` 后显示对应风险值。
- [x] 1.3 处理非法/缺失来源与哈希规范化 — `backend/tests/test_predict_api.py`；同一命令断言固定 50000 不泄露路径、40 位格式校验与大小写一致。

## 2. 跨线真实交付

- [ ] 2.1 模型线蒋励向 backend 吕建江交付可访问的 Camel Git 副本、expert 在线权重与 `data_model/pipelines/expert/models/feature_order.txt`；后端按 `docs/api/predict.md` 对新 hash 完成真实 HTTP 演示并提供可打开的测试证据。权重和 Git 副本不入库，本条未交付前保持未勾选。
- [ ] 2.2 以真实 Camel 新提交和已加载模型分别测量启动、首次请求及 100 次调用的 p95 — 结果写入实际测试报告并给出可打开路径；未达性能目标时如实记录，不静默降级。

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 来源仓库读取、现算落库、幂等、大小写、错误码、详情显式模型查询 |
| 测试文件 | `backend/tests/test_predict_api.py` |
| 用例数与结果 | 原提案记录为 103 passed，属于当时环境；当前提交须重跑并附可复现输出，真实 Camel 未测 |
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
| 关键断言 | 14 项列序相同、重复不增行、详情显式指定已预测模型时显示该模型结果 |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/predict-api/spec.md`、`specs/query-api/spec.md` 的新增场景 |
| 用例数与结果 | 合成场景为原提案记录；真实 Camel 和浏览器联调待验收 |
| 复现命令 / 步骤 | `cd backend && python -m pytest -o addopts='' -q`；`openspec validate on-demand-commit-prediction --strict --no-interactive` |
| 证据归档 | 原路径 `backend/scripts/evidence/on-demand-commit-2026-10-23.md` 已移除；需在实际测试报告中补新证据，未补前不得视为验收通过 |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是，尚未验收 | 真实 Camel 首次请求及 100 次 p95 证据缺失；需补现行测试报告 |
| 安全 | 是 | 来源路径仅服务端环境配置、50000 不回显路径；`cd backend && python -m pytest -o addopts='' -q tests/test_predict_api.py` |
| 可靠 | 是 | 同键幂等、异常来源拒绝、列序来自模型线；同上 |
| 易用 | 间接触及 | 详情按所选模型查询须重新走查；浏览器四页证据待补 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| Camel 完整历史、副本 HEAD 及 CSV 不在当前工作环境 | 原始数据和模型权重按规则不入库，需队友交付 | model 蒋励 / backend 吕建江 | 联调交付时 |
| 首次新提交全量历史扫描可能超过 500ms | 模型线单条入口复用批量算法，尚无索引预热或缓存 | model 蒋励 / backend 吕建江 | 真实 Camel 100 次压测后优化 |
| 模型推理与特征现算时延未按现行权重重测 | 旧报告不能代表当前权重和 Git 数据规模 | model 蒋励 / backend 吕建江 | 真实权重压测并记录结果 |
| 前端四页真实走查与截图缺失 | 当前只测 HTTP 合成链路 | frontend 刘帅华 / PO 苏哲勋 | 四页联调后 |

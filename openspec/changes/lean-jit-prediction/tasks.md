# lean-jit-prediction — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无独立 design.md ｜ 规格：`specs/predict-api/spec.md`
> 负责人：跨线（吕建江、刘帅华） ｜ 创建：2026-10-27 ｜ 状态：进行中（以任务勾选和证据为准）
> 关联需求：未登记编号（见 proposal.md，待负责人补关联）
> 统一格式见 `docs/common/openspec-task-template.md`；末尾「测试与验证」为强制板块。

> 原则：**库内数据只由实时同步决定；不做种子、不做离线导入、不做历史回填。**

## 1. 全站默认模型解析

- [ ] 1.1 `services/settings.py` 增加 `champion_model` 键（与阈值共用同一份缓存），未配置时回退 `version_key` 最大者 — `backend/app/services/settings.py`
- [ ] 1.2 `model_registry` 暴露 `champion()`：读运行时配置，模型未加载时回退 `default_model()` 并记一次日志 — `backend/app/model_registry.py`
- [ ] 1.3 `POST /api/predict` 与读路径共用 `services/champion.py` 有效默认模型解析，响应回显实际模型 — `backend/app/services/predict.py`
- [ ] 1.4 `PUT /api/config` 支持写 `champion_model`（必须是已加载模型，否则 40001） — `backend/app/api/runtime_config.py`

## 2. 批量入口按全部已加载模型落库

- [ ] 2.1 `predict_commit_all_models()` 拆成按模型清单执行：一次特征提取、按清单打分 — `backend/app/api/predict.py`
- [ ] 2.2 `POST /api/sync`、`/api/sync/catchup`、`/api/sync-prs` 默认对全部已加载模型落预测行；核对响应中的模型清单与实际注册表一致 — `backend/app/api/{sync,prs}.py`
- [ ] 2.3 启动同步与 webhook 分支保持各自提交范围上限，但不缩减每条提交的模型集合 — `backend/app/api/{sync,webhook}.py`
- [ ] 2.4 前端同步/补齐提示按全模型实际处理量展示，不能声称默认只运行冠军 — `frontend/src/views/{RiskList,PrList}.vue`

## 3. 「只保留最新」的边界

- [x] 3.1 **删除种子链路**（2026-10-27 已执行）：[历史版 `backend/scripts/seed_dev_data.py`](https://github.com/heapcluster/jit-defect-prediction/blob/100008e787c8902c35760c9cef6d61d279d921b7/backend/scripts/seed_dev_data.py) 删除；`infra/setup_mysql.py` 去掉 `--seed` 参数与 `run_seed()`，完成提示改为「起服务后 `POST /api/sync?limit=10`」 — 证据：`ruff check infra` 通过、`setup_mysql.py` 语法校验通过
- [ ] 3.2 将“只同步最新 N 条、默认全部已加载模型”同步到现行 `docs/overview.md`、`docs/api/sync.md` 和 `docs/function_point/sync.md`；旧文档已随 #187 删除，原勾选不能作为现行证据；待对应文档负责人确认并提供 PR 链接后勾选。
- [ ] 3.3 `limit` 越界（> 50）返回 40001，不静默截断；`sync/catchup` 与 `sync` 的 `limit` 语义统一为「最新 N 条」 — `backend/app/api/sync.py`
- [ ] 3.4 空库首启引导：前端空态只说「拉取最新 N 条」（含 `limit` 说明与预计耗时），`MUST NOT` 出现「导入/初始化/回填/种子」字样 — `frontend/src/views/RiskList.vue`
- [ ] 3.5 数据稀疏的空态：趋势页数据点 < 2、质量看板 0 样本时的文案复核，避免被误读成「功能坏了」 — `frontend/src/views/{TrendBoard,QualityBoard}.vue`

## 4. 阈值按评审预算（phase 2，可与 1~3 分开合）

- [ ] 4.1 把 `reports/model_metrics.md` 的 effort-aware 曲线整理为前端可读的静态 JSON（阈值 → Recall@20/@50） — `frontend/src/utils/`
- [ ] 4.2 质量看板增加「按预算」区块，阈值滑块联动曲线 — `frontend/src/views/QualityBoard.vue`
- [ ] 4.3 校准逻辑增加「按 Recall@N% 目标选阈值」备选模式（仍写 `runtime_setting`） — `backend/app/services/quality.py`

## 测试与验证（强制板块）

### 1. 单元测试

- `backend/tests/test_sync_api.py`：默认全模型落 N 行；重复调用不增加同键行；`limit=5000` → 40001
- `backend/tests/test_predict_api.py`：冠军与有行回退统一解析，响应 `model_name` 正确
- `frontend/tests/`：空库引导文案不含「导入/初始化/回填」；同步按钮按默认全模型解释工作量

### 2. 集成测试

- 空库首启：`POST /api/sync?limit=10` → `GET /api/commits` 的 `total` 恰为 10，无额外行
- 重复同步同一 limit：第二次 `new=0`、`prediction` 行数不变
- 从空库到可用界面的耗时记录（10 条 ≈ 0.5~1.5 分钟，作为文档里的预期值）

### 3. 验收测试

- 按 `specs/predict-api/spec.md` 逐条走：冠军缺省 / 冠军未配置回退 / 默认全模型 / 幂等 / 空库首启 / 越界拒绝 / 启动不追历史 / 事件不越界
- 证据：`prediction` 对每提交每已加载模型各有至多一行、空库首启记录、`pytest` 与 `npm run test:unit` 的当前提交结果；未实测项保持未完成

### 4. 非功能验证

- 写入量：上限为本次同步提交数 × 已加载模型数；需按 `limit` 实测行数与耗时，不以全量历史 67 万行估算替代测量。
- 一致性：`risk_score` 仍为同一模型 `predict_proba` 的正类概率，口径不变

### 5. 已知缺口与后续计划

- **新库数据必然稀疏**：只有最新 N 条，趋势看板可能画不出折线（数据点 < 2 走明细表兜底）、质量看板 0 样本。这是数据的真实状态，需靠空态文案说清，不靠造数据掩盖。
- 已有历史预测行不回删；新同步提交也按全部已加载模型写入，需测试混杂期缺行补齐和幂等行为。
- `limit` 上限 50 意味着「填满一个像样的演示库」本身就不可能——这是刻意的：库里只回答「现在」，历史分析走离线报告。

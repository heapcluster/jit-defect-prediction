# lean-jit-prediction — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/predict-api/spec.md`
> 创建：2026-10-27 ｜ 状态：待实现
> 原则：**库内数据只由实时同步决定；不做种子、不做离线导入、不做历史回填。**

## 1. 服务模型收敛（冠军单跑）

- [ ] 1.1 `services/settings.py` 增加 `champion_model` 键（与阈值共用同一份缓存），未配置时回退 `version_key` 最大者 — `backend/app/services/settings.py`
- [ ] 1.2 `model_registry` 暴露 `champion()`：读运行时配置，模型未加载时回退 `default_model()` 并记一次日志 — `backend/app/model_registry.py`
- [ ] 1.3 `POST /api/predict` 的缺省 `model_name` 改走 `champion()`，响应回显实际模型 — `backend/app/api/predict.py`
- [ ] 1.4 `PUT /api/config` 支持写 `champion_model`（必须是已加载模型，否则 40001） — `backend/app/api/runtime_config.py`

## 2. 批量入口的模型范围

- [ ] 2.1 `predict_commit_all_models()` 拆成按模型清单执行：一次特征提取、按清单打分 — `backend/app/api/predict.py`
- [ ] 2.2 `POST /api/sync`、`/api/sync/catchup`、`/api/sync-prs` 增加 `all_models`（默认 `false`），响应补 `models` 数组 — `backend/app/api/{sync,prs}.py`、`app/schemas.py`
- [ ] 2.3 启动同步与 webhook 分支显式走「冠军单跑」，并断言不触发更大范围扫描 — `backend/app/api/{sync,webhook}.py`
- [ ] 2.4 前端：同步/补齐按钮语义不变；「八模型对比」改为显式勾选（走 `all_models=true`） — `frontend/src/views/{RiskList,PrList}.vue`

## 3. 「只保留最新」的边界

- [x] 3.1 **删除种子链路**（2026-10-27 已执行）：`backend/scripts/seed_dev_data.py` 删除；`infra/setup_mysql.py` 去掉 `--seed` 参数与 `run_seed()`，完成提示改为「起服务后 `POST /api/sync?limit=10`」 — 证据：`ruff check infra` 通过、`setup_mysql.py` 语法校验通过
- [x] 3.2 文档同步去种子：`docs/backend/acceptance.md` §2、`docs/frontend/integration-log.md` §0（建库/数据来源/启动三行）、`docs/owners/s1mple-less.md`（负责范围与联调库）、`data_model/pipelines/expert/README.md` §4 — 证据：全仓 `grep seed_dev_data` 仅剩 `backend/scripts/evidence/**` 与 `openspec/changes/archive/**` 等历史归档
- [ ] 3.3 `limit` 越界（> 50）返回 40001，不静默截断；`sync/catchup` 与 `sync` 的 `limit` 语义统一为「最新 N 条」 — `backend/app/api/sync.py`
- [ ] 3.4 空库首启引导：前端空态只说「拉取最新 N 条」（含 `limit` 说明与预计耗时），`MUST NOT` 出现「导入/初始化/回填/种子」字样 — `frontend/src/views/RiskList.vue`
- [ ] 3.5 数据稀疏的空态：趋势页数据点 < 2、质量看板 0 样本时的文案复核，避免被误读成「功能坏了」 — `frontend/src/views/{TrendBoard,QualityBoard}.vue`

## 4. 阈值按评审预算（phase 2，可与 1~3 分开合）

- [ ] 4.1 把 `reports/model_metrics.md` 的 effort-aware 曲线整理为前端可读的静态 JSON（阈值 → Recall@20/@50） — `frontend/src/utils/`
- [ ] 4.2 质量看板增加「按预算」区块，阈值滑块联动曲线 — `frontend/src/views/QualityBoard.vue`
- [ ] 4.3 校准逻辑增加「按 Recall@N% 目标选阈值」备选模式（仍写 `runtime_setting`） — `backend/app/services/quality.py`

## 测试与验证

### 单元测试

- `backend/tests/test_sync_api.py`：默认单模型落 1 行；`all_models=true` 落 N 行；重复调用 `new=0`；`limit=5000` → 40001
- `backend/tests/test_predict_api.py`：champion 未配置时回退 `version_key` 最大者，响应 `model_name` 正确
- `frontend/tests/`：空库引导文案不含「导入/初始化/回填」；同步按钮在 `all_models` 关闭时不再暗示八模型都会跑

### 集成测试

- 空库首启：`POST /api/sync?limit=10` → `GET /api/commits` 的 `total` 恰为 10，无额外行
- 重复同步同一 limit：第二次 `new=0`、`prediction` 行数不变
- 从空库到可用界面的耗时记录（10 条 ≈ 0.5~1.5 分钟，作为文档里的预期值）

### 验收测试

- 按 `specs/predict-api/spec.md` 逐条走：冠军缺省 / 冠军未配置回退 / 默认单模型 / 显式全模型 / 幂等 / 空库首启 / 越界拒绝 / 启动不追历史 / 事件不越界
- 证据：`prediction` 行数前后对比（8 行/提交 → 1 行/提交）、空库首启记录、`pytest` 与 `npm run test:unit` 全绿

### 非功能验证

- 写入量：演示库 `prediction` 行数由约 67 万降至「提交数 × 1」
- 一致性：`risk_score` 仍为同一模型 `predict_proba` 的正类概率，口径不变

## 已知缺口与风险

- **新库数据必然稀疏**：只有最新 N 条，趋势看板可能画不出折线（数据点 < 2 走明细表兜底）、质量看板 0 样本。这是数据的真实状态，需靠空态文案说清，不靠造数据掩盖。
- 已有 8 行/提交的历史数据不回删，新旧数据混杂期「切非冠军模型」的表现需要文档说明（旧提交能切 8 个，新提交只有冠军）。
- `limit` 上限 50 意味着「填满一个像样的演示库」本身就不可能——这是刻意的：库里只回答「现在」，历史分析走离线报告。

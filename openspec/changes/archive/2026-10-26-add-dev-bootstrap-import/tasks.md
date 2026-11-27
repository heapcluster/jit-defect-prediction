# add-dev-bootstrap-import — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无 `design.md`（边界说明已写进 delta） ｜ 规格：`specs/db-schema/spec.md`
> 负责人：backend（本机打通运行环境时一并落地）｜ 创建：2026-10-26 ｜ 状态：已实现并归档
> 用户故事：无（工程化：让 clone 完的人十分钟内看到真实数据的三页）

## 1. 规格 delta

- [x] 1.1 `db-schema`：MODIFIED「实时同步入库」—— 禁令限定为**运行时入口**，补「本地开发初始化」例外与边界 Scenario
- [x] 1.2 `db-schema`：ADDED「本地开发数据初始化」—— 读什么、写什么、幂等口径、命令行参数

## 2. 代码

- [x] 2.1 新增 `infra/bootstrap_dev.py`：导入 `commits.csv` / `commit_features.csv` / `dataset_szz.csv`，按 `--limit` 取最新 N 条，`--reset` 清空重建，`--skip-predict` 只导数据
- [x] 2.2 预跑预测：`--models` 指定模型（默认 `xgb_v1`），走 `model_registry` 真实权重，写 `prediction` 并按 `(commit_hash, model_name)` 跳过已有行
- [x] 2.3 `infra/setup_mysql.py`：`CREATE USER IF NOT EXISTS` 对已存在账号不改口令 → 补 `ALTER USER` 同步口令，并建 `jit@127.0.0.1`（本机实测 1045 的真因）
- [x] 2.4 `infra/setup_mysql.py`：DDL 里的用户名/口令做单引号转义（口令含 `'` 不再拼出坏 SQL）

## 3. 文档

- [x] 3.1 `README.md`：Quick Start 改为「配 `.env` → `setup_mysql.py` → `bootstrap_dev.py` → 起后端/前端」
- [x] 3.2 `docs/backend/mysql-setup.md`：新增坑 13（账号已存在但口令不同 → 1045）与初始化脚本用法
- [x] 3.3 `docs/common/local-runbook.md`：一条命令灌演示数据

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | `bootstrap_dev` 的幂等与参数；`setup_mysql` 的连接解析（已有 8 条） |
| 测试文件 | `infra/tests/test_setup_mysql_credentials.py` |
| 用例数与结果 | **29 passed**（工程化套件全量，含本次新增的 8 条） |
| 复现命令 | `python -m unittest discover -s infra/tests -p 'test_*.py'` |
| 正向用例 | 分字段 / 命令行 / 整段 DSN 三种来源都能解析出口令与库名 |
| 异常 / 边界用例 | 缺配置与非法端口均 `SystemExit` 且提示具体字段 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 真实 MySQL 8.0.45：建库建表 → 导入 3000 条 → 预跑预测 → 起 uvicorn → 打四个接口 |
| 测试文件 | 无新增自动化用例（一次性环境验证，见下「关键断言」） |
| 用例数与结果 | `commit=3000` / `commit_label=2941` / `commit_feature=3000` / `prediction=6000`；`risk>=0.5` 1130 条 |
| 复现命令 | `python infra/bootstrap_dev.py --limit 3000 --models xgb_v1,lr_v1`；`cd backend && uvicorn app.main:app` |
| 关键断言 | `GET /api/commits` → `total=3000`；`GET /api/commits/{hash}` → 14 特征 + 14 条 SHAP；`GET /api/trends` → 4 个月桶；`POST /api/predict` → `risk=0.99964`；不存在的哈希 → `40400` |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `db-schema`「本地开发数据初始化」3 个 Scenario + 「实时同步入库」4 个 Scenario |
| 用例数与结果 | 7/7 逐条核对通过（含「重复执行不产生重复行」与「初始化后同步仍正常」） |
| 复现命令 / 步骤 | 同上；重复执行 `bootstrap_dev.py` 观察四表行数不变 |
| 证据归档 | 本 change 的 tasks 记录 + `backend/tests/` 回归（`pytest` 263 passed） |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是（初始化耗时） | 3000 条导入 + 2 模型预跑在本机约 1 分钟；默认 5000 条 |
| 安全 | 是 | 口令不进日志、不 print；`.env` 已被 `.gitignore` 忽略 |
| 可靠 | 是 | 重复执行幂等；`--reset` 显式清空，脚本本身不做破坏性操作 |
| 易用 | 是 | 一条命令得到可演示的三页数据；README 三步启动 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| `bootstrap_dev.py` 没有自动化用例 | 需要真实 MySQL 与 600MB 权重，成本高于收益 | backend | 若要纳入 CI，需先加「小样本 fixture」 |
| 历史行不含 `prediction` 的 SHAP 归因缓存 | 归因在 `GET /api/commits/{hash}` 现算（按模型惰性构造 explainer） | 无 | 不排期 |

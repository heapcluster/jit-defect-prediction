# 本机跑通手册（建库 → 灌数 → 起服务 → 前端预测）

> 目标：一个人在自己机器上，从零到「前端点开就能预测 Apache Camel 提交」，全程可复制。
> 范围：expert 线 + 后端四接口 + 前端三页面。不含其他仓库、不含其他模型线。
> 权威边界：**联调基线（库文件 / seed / 令牌 / 端口 / `MODEL_DIR`）的唯一出处是 `docs/frontend/integration-log.md` §0**，本文件只给「本机怎么落地」，不复述 §0 的字面值；两者冲突以 §0 为准。

---

## 0. 前置

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.12.x | 权重由 sklearn 1.9.1 训练，主版本别跨 |
| Node | 20.x | 前端 `npm run dev` |
| MySQL | 8.x | 想用 MySQL 建库才需要；SQLite 开箱可用 |
| Git | 任意 | 现算特征要对本地 Camel 副本执行 `git log` |

依赖安装以 `docs/model/ENVIRONMENT.md`（data_model 侧）与 `backend/README.md`（后端侧）为准，本文件不重复列包名。

---

## 1. 取权重（唯一需要手工传的东西）

`.pkl` 与 `data/` 下的 CSV **都不入库**，`clone` 拿不到，必须手工摆。

```powershell
# 1) 拿包：expert_models_20261024.zip（110,492,842 B）
Get-FileHash .\expert_models_20261024.zip -Algorithm MD5
# 期望 57520463da2b94592842707874ab8c0d（包级 md5，先核包再解压）

# 2) 解压到 models/，10 个文件必须平铺（不要再套一层文件夹）
Expand-Archive .\expert_models_20261024.zip -DestinationPath .\data_model\pipelines\expert\models -Force

# 3) 先看 rf 大小：12,715,033 B 才是 D-14 收敛版；292,996,489 B 说明拿到旧包
(Get-Item .\data_model\pipelines\expert\models\rf_v1.pkl).Length

# 4) 清单校验：8 个权重逐个回读 + md5 + 类路径 + 特征宽度
cd data_model; python -m pipelines.verify_all_weights --check
# 期望：清单一致（8 项）/ 全部通过：8/8 可加载，特征宽度 [14]
```

> 权重不入库、只靠包转发，**同名不同版是真事**（D-15 的 TabNet 分叉就是这么来的）：一律以 md5 对齐，不以文件名对齐。

---

## 2. 建库

两条路都能建出同样的四张表（`commit` / `commit_label` / `commit_feature` / `prediction`）。**先选定一条，别在同一个库上混用**：两条路径的等价性已在 MySQL `jit_demo` 实测（DDL 与 ORM 双路径幂等 + `_assert_indexes` 通过，2026-10-25 组长本机复测）；**Issue #121 是真库验收的探针库，与本演示库无关**。

### 2.1 建库建号（MySQL，本机自建）

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS jit_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER IF NOT EXISTS 'jit'@'127.0.0.1' IDENTIFIED BY '<自己设的密码>';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON jit_demo.* TO 'jit'@'127.0.0.1'; FLUSH PRIVILEGES;"
```

### 2.2 建表（二选一）

```bash
# A. ORM 路径（推荐，会顺带跑 _assert_indexes 自检）
cd backend
DATABASE_URL="mysql+pymysql://jit:<密码>@127.0.0.1:3306/jit_demo?charset=utf8mb4" python -m app.db init

# B. DDL 路径（部署形态，脚本在 infra/，自带 CREATE DATABASE + USE）
mysql -u root -p < ../infra/schema.sql
```

两种都要满足：**连跑两次不报错（幂等）**，且下面这条自检通过：

```bash
cd backend
DATABASE_URL="mysql+pymysql://jit:<密码>@127.0.0.1:3306/jit_demo?charset=utf8mb4" \
  python -c "from app.db import get_engine, _assert_indexes; _assert_indexes(get_engine()); print('indexes ok')"
```

> 索引自检只覆盖 `INDEX_ASSERTIONS` 里的核心索引，不等于完整列/键对照；完整验收按 `docs/backend/acceptance.md` 板块 B1。

### 2.3 不装 MySQL 的退路

SQLite 开箱可用，也是**联调基线的库形态**：

```bash
cd backend && python -m scripts.seed_dev_data   # 建 backend/dev.db 并灌 3 提交 / 3 特征 / 3 预测
```

---

## 3. 灌真实数据（可选）

不灌也能验收「模型加载 + 单条在线预测」；要三页面有真实规模数据才灌。CSV 来自数据线产物（`01–04 + 07`），或用交付包 `deliver_data_20261024.zip`（18,006,911 B / md5 `601f5fceac3105273d98fb7eedfcb360`）。

```bash
# cwd=backend，顺序不能换（commits → features → predictions）
python -m app.ingest commits     <目录>/commits.csv
python -m app.ingest features    <目录>/commit_features.csv
python -m app.ingest predictions <目录>/prediction_result.csv
```

幂等：同一文件重跑不增行（按表幂等键 upsert）；缺主键字段的行整批回滚并报行号。
`GET /api/commits` 是 `prediction` 内连接，`commits.csv` 灌全量（约 45 万条）不会把「无预测的提交」带进风险列表。

---

## 4. 起后端

`backend/.env`（模板见 `backend/.env.example`，实际值不进 git）：

```ini
DATABASE_URL=mysql+pymysql://jit:<密码>@127.0.0.1:3306/jit_demo?charset=utf8mb4
API_TOKEN=<与服务端一致的令牌>
MODEL_DIR=                       # 留空 = 回落到 data_model/pipelines/expert/models/
SOURCE_REPO=<本地 Apache Camel 仓库绝对路径>   # 只在本机 .env.local 写，不进文档、不进 .env.example
```

> `SOURCE_REPO` 是「现场预测新提交」的开关：不配时，`POST /api/predict` 只查库，库里没有的哈希一律 40400。
> 配了之后后端会调 `data_model/preparation/03_extract_features.py` 现算 14 项特征，**首次会扫 Git 历史，别拿它做性能验收**。
> `backend/.env.example` 已含 `SOURCE_REPO` 与 `jit_demo` 模板（2026-10-25 统一口径，PR 见仓库）。

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 启动日志应出现：loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']，且没有 failed models / model load failed
```

---

## 5. 起前端

```bash
cd frontend
# .env.local（已被 .gitignore）：VITE_API_KEY 必须与后端 API_TOKEN 一致
npm install
npm run dev
```

---

## 6. 验收清单（点完这 6 条就算链路通）

| # | 动作 | 期望 |
|---|---|---|
| 1 | `GET /api/commits?page=1&size=10` | `code=0`，`total` 与库内预测行数一致，按 `risk_score` 降序 |
| 2 | `GET /api/commits/<库内某个 40 位哈希>` | `features` 14 项齐全，`explanation` 非空 |
| 3 | `GET /api/trends?granularity=month` | `series` 非空，`high_risk_count` 由后端算（阈值 0.5，前端不重算） |
| 4 | `POST /api/predict` 传库内哈希 | `risk_score` + `predicted_at` + 14 项 features + SHAP 归因；重复调两次库里仍只有一行 |
| 5 | `POST /api/predict` 传**库外**的 Camel 提交（需配 `SOURCE_REPO`） | 现算特征后返回预测；不配 `SOURCE_REPO` 时应为 40400 |
| 6 | 前端三页面（风险列表 / 提交详情 / 趋势看板） | 详情页「重新预测」可选 `lr_v1` / `rf_v1` / `xgb_v1`，点完 `risk_score` 与 `model_name` 立刻刷新 |

---

## 7. 8 个模型可切换：现状与差距（未落地，别当已支持）

**现状是 3 个**：`feature_order.txt` 的 `[models]` 段声明 `lr_v1` / `rf_v1` / `xgb_v1`，`model_registry` 只加载这一段；另 5 个（`lgbm_v1` / `et_v1` / `svm_v1` / `mlp_deep_v1` / `tabnet_v1`）在 `[evaluated]` 段，只进评估。传这 5 个的 `model_name` 会返回 **40001 参数非法**。

要变成 8 个，缺 6 件事：

| # | 缺什么 | 归谁 | 后果 / 代价 |
|---|---|---|---|
| 1 | 契约三 §4 的 `model_name` 枚举 3→8；解除 `openspec/specs/model-coverage` R6 冻结（「新增模型 MUST NOT 进入后端加载清单」） | 契约/infra（苏哲勋）+ 模型线（蒋励） | 必须走 change，不能静默改 |
| 2 | `models/feature_order.txt` 的 `[models]` 加 5 行 | 模型线（蒋励） | 5 分钟，但依赖第 1 条先裁 |
| 3 | 后端依赖加 `lightgbm`、`torch`（`tabnet` 还需 `pytorch_tabnet`） | 后端（吕建江） | 镜像约 +250MB，冷启动变慢 |
| 4 | **SHAP 归因**：现有 `get_explainer` 只有 `TreeExplainer`（树族）与 `LinearExplainer`（有 `coef_`）。`svm`（RBF）/ `mlp_deep` / `tabnet` **两者都不适用** → 现在只会降级成空归因（前端「无归因」），要真归因得上 `KernelExplainer` | 模型线 + 后端 | KernelSHAP 单次 1–3s，**500ms 靶子必破**；要么接受「这 3 个模型无归因」，要么按模型分别定靶子（又是 change） |
| 5 | 8 个模型各按登记口径 `perf_loop.py --n 100` 压测（每个都要单模型 `MODEL_DIR`） | 后端（吕建江） | 半天；注意 `perf_loop.py` **没有** `--model-name` 参数 |
| 6 | 前端 `src/utils/models.js` 的静态清单 3→8 | 前端（刘帅华） | 1 行，且必须与 `[models]` 段同步，否则下拉静默少项 |

**判断**：第 3、4 条是真正的成本，第 1 条是流程成本。MVP 建议维持 3 个（已全部达标：默认 xgb p95 15.5ms、rf 86.6ms、lr 9.0ms）；8 个切换按 change 单独立项，别塞进 D-14 这批。

---

## 8. 故障对照

| 现象 | 最可能原因 | 处理 |
|---|---|---|
| 启动日志 `failed models: [...]` | 权重版本不对 / 缺依赖 / 目录里套了子文件夹 | `verify_all_weights --check` 看 md5 与类路径；确认 10 个文件平铺 |
| 所有接口 `50000 internal error` | `DATABASE_URL` 为空或不可达 | 按 §2 建库并核对连接串；日志在服务端，不回显给你 |
| `40100` | 前后端令牌不一致 | 前端 `VITE_API_KEY` 与后端 `API_TOKEN` 必须是同一个 |
| `40400` 且哈希确实存在 | 没灌 `commit` / `commit_feature`，且未配 `SOURCE_REPO` | 灌数（§3）或配 `SOURCE_REPO`（§4） |
| `40001 参数非法：model_name` | 选了 `[evaluated]` 里的模型 | 只用 `lr_v1` / `rf_v1` / `xgb_v1`（8 模型见 §7） |
| 预测值眼熟但和旧记录不一样 | rf 权重已换成收敛版（md5 `ca80c586…`），旧 `prediction` 行不可比 | 用新权重对要展示的哈希重跑一次 |
| 第一次 predict 很慢（>1s） | SHAP 解释器惰性构造（首请求） | 正常，判定看 p95 不看 max |

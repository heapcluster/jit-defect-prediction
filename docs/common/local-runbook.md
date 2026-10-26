# 本机跑通手册（建库 → 灌数 → 起服务 → 前端预测）

> 目标：一个人在自己机器上，从零到「前端点开就能预测 Apache Camel 提交」，全程可复制。
> 范围：expert 线 + 后端四接口 + 前端三页面。不含其他仓库、不含其他模型线。
> 权威边界：**联调基线（库文件 / seed / 令牌 / 端口 / `MODEL_DIR`）的唯一出处是 `docs/frontend/integration-log.md` §0**，本文件只给「本机怎么落地」，不复述 §0 的字面值；两者冲突以 §0 为准。

---

## 0. 前置

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.12.x | 权重由 sklearn 1.9.1 训练，主版本别跨 |
| Node | ≥20.19（CI 用 24） | 前端 `npm run dev`；vite 8 / vitest 5 要求 Node ≥20.19 |
| MySQL | 8.x | 联调 / 演示 / 验收统一数据库，本机必须安装（建库见 `infra/setup_mysql.py`）|
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

统一用 MySQL（联调 / 演示 / 验收同一套 `jit_demo`），不再保留 SQLite 联调库。两种建表路径（ORM / DDL）等价且幂等，已在本机 MySQL `jit_demo` 实测（2026-10-25 组长复测）；**Issue #121 是真库验收的探针库，与本演示库无关**。

### 2.1 一键建库（推荐）

克隆后配好 `backend/.env` 的 `DATABASE_URL`（指向本机 MySQL 的 `jit_demo`，账密自己设），然后：

```bash
python infra/setup_mysql.py            # 读 backend/.env，建 jit_demo + 测试库 jit_test 并跑 schema.sql
python infra/setup_mysql.py --seed     # 额外灌 3 提交 / 3 特征 / 3 预测起步数据
```

脚本会先尝试启动本机 MySQL 服务（Windows / Linux / macOS 各自一行命令），再建库、建应用用户 `jit`、执行 `infra/schema.sql` 建四张表。若 `jit` 无建库权限，加 `--root-password <pwd>` 由 root 代建并授权。

### 2.2 手动分步（可选，等价于一键）

```bash
# 1) 建库建号（MySQL 8 普通账号默认无 CREATE DATABASE，建库用 root）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS jit_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER IF NOT EXISTS 'jit'@'127.0.0.1' IDENTIFIED BY '<自己设的密码>';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON jit_demo.* TO 'jit'@'127.0.0.1'; FLUSH PRIVILEGES;"

# 2) 建表（二选一）
# A. ORM 路径（推荐，会顺带跑 _assert_indexes 自检）
#    连接串写 backend/.env（DATABASE_URL=mysql+pymysql://jit:<密码>@127.0.0.1:3306/jit_demo?charset=utf8mb4）
cd backend && python -m app.db init

# B. DDL 路径（部署形态）
mysql -u jit -p jit_demo < ../infra/schema.sql
```

两种路径都要满足：**连跑两次不报错（幂等）**，且下面这条自检通过：

```bash
cd backend
python -c "from app.db import get_engine, _assert_indexes; _assert_indexes(get_engine()); print('indexes ok')"
```

> 索引自检只覆盖核心索引，不等于完整列/键对照；完整验收按 `docs/backend/acceptance.md` 板块 B1。

### 2.3 建 Camel blobless 历史索引（实时预测必需）

实时预测 Camel 的 PR 需要一份**只读历史索引**来算 14 维特征里的历史类（`ndev/age/nuc/exp/rexp/sexp`）。它用 blobless 克隆（只取提交+树、不含 blob，几十 MB），**不是开发库、不进工作流**：

```bash
python infra/clone_camel_history.py --repo apache/camel --path ../camel-history
# 之后在 backend/.env 设 SOURCE_REPO=<该路径>
```

脚本内部执行 `git clone --filter=blob:none --no-checkout` 建索引，并提供 `fetch` 子命令增量更新；`SOURCE_REPO` 指向它即可，预测时只跑 `git log --numstat` / `git cat-file`，不碰工作区。

---

## 3. 灌数据：实时同步 Camel 最新 PR（唯一入口）

系统**只走实时预测**：不再有离线 CSV 灌库。数据来源是 GitHub 上 `apache/camel` 的 open PR，特征在本地 blobless 历史索引上现算、逐模型打分入库。

```bash
# 1) 启动后端后，拉取最新 open PR 并逐条现算预测（默认 10 个 PR，上限 50）
curl -X POST "http://127.0.0.1:8000/api/sync-prs?limit=20" -H "X-API-Key: $API_TOKEN"

# 2) 前端「PR 列表」页即可看到各 PR 的聚合风险；点进 PR 看每个 commit 的风险
```

> 离线 CSV 灌库（`python -m app.ingest`）已于 2026-10-25 裁定**彻底移除**（脚本、CLI 入口与测试一并删除）；历史口径的 CSV 产物仅作数据线归档，不再进入运行时。数据入口只有 §3.1 的实时同步（主干）与 §3.2 的 open PR 同步。

幂等：同一提交重复同步不增行（按表幂等键 upsert：commit=commit_hash、label=(commit_hash, label_method)、feature=commit_hash、prediction=(commit_hash, model_name)）；单条失败只计入 `skipped`，不中断整批。
`GET /api/commits` 是 `prediction` 内连接，「库中无预测的提交」不会进风险列表。

### 3.1 实时同步（change `realtime-commit-sync`，新数据入口）

**系统只预测 Camel 最新提交**（2026-10-25 蒋励裁定）：后端对 `SOURCE_REPO` 执行 fetch → 挑出库中不存在（或默认模型尚未预测）的新提交 → **逐条现算 14 项特征 → 模型推理 → 入库 → 列表自动排序**。

```bash
# 起后端后（§4）：批量同步最近 N 条（默认 10，上限 50）
curl -X POST 'http://127.0.0.1:8000/api/sync?limit=50' -H 'X-API-Key: <令牌>'
```

返回 `{tip, scanned, new, predicted[], skipped[]}`：`new=0` 表示无待预测提交（幂等）；单条失败（如提交不可达）计入 `skipped`，其余继续。`SOURCE_REPO` 未配置 → 40400；`limit` 越界 → 40001；同一时刻只允许一个同步任务。

> **耗时与演示方式**：单条约 3~8 秒（含全量历史扫描 + SHAP），`limit=50` 最坏约数分钟且 HTTP 同步挂起 —— 演示一律用 `SYNC_ON_STARTUP=1` 启动预同步，或现场只发小 `limit`。
> **口径提醒**：本地 Camel clone 的历史深度会影响过程特征（exp/ndev/nuc/age），同一提交在不同深度算出的 risk 可能不同（实测 0.54 → 0.22）。每人 clone 后建议 `git fetch --unshallow`（至少覆盖近半年），保证各机器可复现。
> **read-only 保证**：远端 tip 不是本地 HEAD 祖先时，后端建**专用临时工作树**（`--no-checkout`）提取特征，用后即焚，**不会改动你正在使用的检出状态**（进程被硬杀时在 SOURCE_REPO 跑一次 `git worktree prune` 清残留）。

---

## 4. 起后端

`backend/.env`（模板见 `backend/.env.example`，实际值不进 git）：

```ini
DATABASE_URL=mysql+pymysql://jit:<密码>@127.0.0.1:3306/jit_demo?charset=utf8mb4
API_TOKEN=<与服务端一致的令牌>
MODEL_DIR=                       # 留空 = 回落到 data_model/pipelines/expert/models/
SOURCE_REPO=<本地 Apache Camel 仓库绝对路径>   # 只在本机 .env.local 写，不进文档、不进 .env.example
# SYNC_ON_STARTUP=1              # 启动时后台预同步一次（默认关，模板行以 backend/.env.example 为准）
```

> `SOURCE_REPO` 是「现场预测新提交 / 批量同步」的开关：不配时，`POST /api/predict` 只查库，库里没有的哈希一律 40400。
> 配了之后后端会调 `data_model/preparation/03_extract_features.py` 现算 14 项特征，**首次会扫 Git 历史，别拿它做性能验收**。

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

## 7. 8 个模型可切换：现状（2026-10-25 组长裁定 Issue #139 已落地）

**现状是 8 个**：`feature_order.txt` 的 `[models]` 段已声明全部 8 个（`lr_v1` / `rf_v1` / `xgb_v1` / `lgbm_v1` / `et_v1` / `svm_v1` / `mlp_deep_v1` / `tabnet_v1`），`model_registry` 加载这一段；`[evaluated]` 段当前为空。前端 `src/utils/models.js` 的静态清单已同步为 8 个。传清单外的 `model_name` 才返回 **40001 参数非法**。

| 项 | 状态 | 说明 |
|---|---|---|
| 契约三 §4 的 `model_name` 枚举 | ✅ 已放开为 8 个 | 走 change 流程，非静默改 |
| `feature_order.txt` 的 `[models]` | ✅ 8 行 | `[evaluated]` 段留空 |
| 后端依赖（`lightgbm` / `torch` / `pytorch_tabnet`） | ✅ 已进 `environment.yml` | 镜像变大、冷启动变慢 |
| **SHAP 归因** | ⚠️ 三个模型无归因 | `svm`（RBF）/ `mlp_deep` / `tabnet` 无高效精确解释器，契约三 §4 允许，详情页显「无归因」；要真归因需 KernelSHAP（单次 1–3s，500ms 靶子必破） |
| 各模型压测 | ✅ 已登记 | 单模型 `MODEL_DIR` 压测；`perf_loop.py` **没有** `--model-name` 参数 |
| 前端静态清单 | ✅ 8 个 | 必须与 `[models]` 段同步，否则下拉静默少项 |

**归因降级**：这三个模型在详情页显示「无归因」是**预期行为**，不是缺陷（契约三 §4 已允许）。

---

## 8. 故障对照

| 现象 | 最可能原因 | 处理 |
|---|---|---|
| 启动日志 `failed models: [...]` | 权重版本不对 / 缺依赖 / 目录里套了子文件夹 | `verify_all_weights --check` 看 md5 与类路径；确认 10 个文件平铺 |
| 所有接口 `50000 internal error` | `DATABASE_URL` 为空或不可达 | 按 §2 建库并核对连接串；日志在服务端，不回显给你 |
| `40100` | 前后端令牌不一致 | 前端 `VITE_API_KEY` 与后端 `API_TOKEN` 必须是同一个 |
| `40400` 且哈希确实存在 | 库中无该提交的历史索引，且未配 `SOURCE_REPO` | 配 `SOURCE_REPO`（§4）后走实时同步（§3） |
| `40001 参数非法：model_name` | 选了交付清单外的模型名 | 只用 `[models]` 段的 8 个（见 §7） |
| 预测值眼熟但和旧记录不一样 | rf 权重已换成收敛版（md5 `ca80c586…`），旧 `prediction` 行不可比 | 用新权重对要展示的哈希重跑一次 |
| 第一次 predict 很慢（>1s） | SHAP 解释器惰性构造（首请求） | 正常，判定看 p95 不看 max |

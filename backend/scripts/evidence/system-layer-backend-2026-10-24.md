# 系统层 T-ST-01~05 的后端半边执行记录（2026-10-24，实跑于 SQLite `demo.db`）

> **⚠ 口径变更说明（2026-10-25 补记，#141 审阅条件 1）**：本记录跑于 **SQLite `backend/demo.db`**，而 **Issue #130 的更正裁定**（蒋励，2026-10-24 追加，覆盖原裁定「一」里的 SQLite 表述）已把**演示库敲定为 MySQL `jit_demo`**（联调库仍是 SQLite `backend/dev.db` 不变，理由：#117 的 9 张三态截图已在该口径下取证并合入，改口径会让取证作废）。因此 **在建库授权（Issue #142）到位、并按同一脚本在 `jit_demo` 上复跑回填之前，本文件只作过程证据，不能作为「MySQL 演示库已验证」的依据**。数据与 43 项断言本身有效：四份 CSV 与 `integration-2026-10-24.md` §2 是同一批真实产物，断言口径（T-ST-04 清单内外分判）也是裁定 A 的原文。复跑结果按「只追加不改写」以补记形式加在本文件末尾，本段与下面的原有数字一律不动。
>
> **文档状态（按 `docs/README.md` §0.2 的三分类交代清楚，避免被读成「第四种状态」）**：本文件是 T-ST-01~05 **后端半边**的验收记录，对该用例仍是**唯一正文（权威）**，只是**演示库口径这一项的适用范围受限**（SQLite 实跑 ≠ MySQL 演示库已验证）。**故不标「历史，不作为现行口径」**——它没有被任何文件取代；MySQL `jit_demo` 的复跑补记**落在本文件末尾**，不另开第二份正文、不倒填原有数字（`docs/repo/collaboration.md` §0 第 4 条口径单点）。

- 依据：**Issue #130 裁定 A**（蒋励，2026-10-24）——演示库与联调库并列登记；T-ST-04 判据改为「清单内 3 个 200、清单外 5 个 40001 属 R6 预期」。原文写的演示库是 `backend/demo.db`，**该处已被同日追加的更正裁定覆盖为 MySQL `jit_demo`**（见文首口径变更说明）；本文件按当时生效的口径执行，故实跑库是 `demo.db`。生成命令将登记在 `docs/repo/demo-script-sprint1.md` §0.0/§0.0.1（PR #136，合入后可点开），本文件只记**执行结果**，不另立口径。
- 范围：**后端能断言的部分**。页面三态与文案（T-ST-02 的"提示重新登录不给重试"、T-ST-03 的"空态而非崩溃"）、下拉渲染（T-ST-04 的前端半边）、录屏（T-ST-01~05 全链路）属前端线与三方同场，**本文件不冒充**。
- 结果：**43 项断言全过，退出码 0**（2026-10-24 23:48 实跑）。

## 1. 演示库的生成与核对

```bash
cd backend
DATABASE_URL="sqlite:///<repo>/backend/demo.db" python -m app.db init
DATABASE_URL=… python -m app.ingest commits     <commits.csv>        # 84,461 行
DATABASE_URL=… python -m app.ingest labels      <labels.csv>        # 83,943 行
DATABASE_URL=… python -m app.ingest features    <features.csv>      # 83,943 行
DATABASE_URL=… python -m app.ingest predictions <predictions.csv>   # 83,943 行
```

四份 CSV 与 `integration-2026-10-24.md` §2 用的是同一批真实产物（commits = `preparation/01_extract_commits` 重跑；labels = 已登记 `dataset_szz.csv` 投影且与 02 独立重跑逐行一致；features/predictions 同左），不现场造数。

**在 MySQL `jit_demo` 上复跑（等 Issue #142 的建库脚本 + 配置文档落地；#142 已改为「每人本机 MySQL」，不再等某台机器的授权）**

连接串写在**本机 `backend/.env`**（`DATABASE_URL=mysql+pymysql://<user>:<pwd>@127.0.0.1:3306/jit_demo?charset=utf8mb4`；真实口令只在本机 `.env`，不写进本文件、不写进任何入库文档 —— `docs/repo/collaboration.md` §0 第 3 条），**并且上面那五条命令要逐条去掉行内 `DATABASE_URL=…` 前缀**：

```bash
cd backend
python -m app.db init                                    # 或走 #142 的建库脚本（DDL 路径）
python -m app.ingest commits     <commits.csv>           # 84,461 行
python -m app.ingest labels      <labels.csv>            # 行数口径见 §6.1
python -m app.ingest features    <features.csv>          # 行数口径见 §6.1
python -m app.ingest predictions <predictions.csv>       # 83,943 行
```

为什么必须去前缀：`backend/app/config.py` 只调用 `load_dotenv()`，而 **`load_dotenv()` 默认不覆盖已存在的环境变量** —— 行内 `DATABASE_URL=…` 会压过 `.env` 里的真实连接串，两种写法只能选一种。原文写的「五条命令一条不改，只把 `DATABASE_URL` 换成 …」与此处的「口令走 `.env`」互相冲突、按占位符执行连不上 MySQL，是 #145 复审（@sober-hub）指出的，已按其改法订正，见 §6.2。

四份 CSV 的路径与文件名以 `docs/repo/demo-script-sprint1.md` §0.0/§0.0.1 为**唯一出处**（§0.0.1 在 PR #136 内，合入后可点开），本文件不另抄一份、不另立口径。期望值不变：commits **84,461**、predictions **83,943**、`risk_score ≥ 0.5` **14,596** 条、列表 `total` **83,943**、启动日志三模型全加载（labels/features 的行数取决于用哪份 CSV，见 §6.1）。复跑与断言用 Issue #138 的 `backend/scripts/demo_preflight.py`（本记录那 43 项断言的驱动脚本已并进它，PR #148），一条命令跑完、任一步不符即退出码 1 并打印实际值。

**本记录仍是 SQLite `demo.db` 上跑的，MySQL 侧未验证**（文首口径变更说明）；MySQL 复跑的结果按「只追加不改写」以补记形式加在本文件末尾。

| 核对项 | 实测 | 期望（裁定/留档） |
|---|---|---|
| 四表行数 | 84,461 / 83,943 / 83,943 / 83,943 | 同左 |
| `risk_score ≥ 0.5` 行数 | **14,596** | 14,596（17.39%） |
| `GET /api/commits` 的 `total` | **83,943** | prediction 内连接，无预测的提交不进列表 |
| `GET /api/commits?min_risk=0.5&size=5` | 5 条，首条 `risk_score=0.9993` | 演示脚本 §0.3 要求至少 1 条 |
| 启动日志 | `INFO:backend.model_registry:loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']`，无 `failed models:` | §0 口径（`MODEL_DIR` 指向已核验交付包目录：zip md5 `57520463…`、rf md5 `ca80c586…`） |

联调库 `dev.db` 本次**没有动**（仍是 seed 3/0/3/3）；两条库各管各的，符合裁定第 1、3 条。

## 2. 43 项断言（按用例分组）

| 用例 | 断言 | 结果 |
|---|---|---|
| **T-ST-01** 正向主链路 | 列表 200 且 `total=83943`；首条带 `risk_score`/`model_name`；详情 200 且 `features` 14 键、`explanation` 非空；趋势 200 且期数 > 0 | 8/8 ✅ |
| **T-ST-02** 无效 Key | 缺令牌 → 401 + `code=40100`；错令牌 → 401 + `code=40100` 且 `message` 为固定文案 `missing or invalid token`（不提示哪一位错） | 4/4 ✅ |
| **T-ST-03** 非法哈希 | 39 位 → `40001`；40 位非十六进制 → `40001`；库外 40 位合法 → `40400` 且 HTTP 404 | 4/4 ✅ |
| **T-ST-04** 八模型按新判据 | 清单内 `lr_v1`/`rf_v1`/`xgb_v1` 逐个 POST → 200、回显同名、`explanation` 非空、键名 ⊆ 契约二 14 特征、无重复特征；清单外 `lgbm_v1`/`et_v1`/`svm_v1`/`mlp_deep_v1`/`tabnet_v1` 逐个 → `40001` | 17/17 ✅ |
| **T-ST-05** 回归 | 不传 `model_name` → 200 且默认 `xgb_v1`（版本序最新）；同哈希再 POST → 200 且 `(hash, xgb_v1)` 仍 **1 行**（幂等）；`size=101` → `40001`；`granularity=decade` → `40001`；`openapi.json` 的 `/api/*` 路径仍为 **4 条**（契约三枚举未变） | 7/7 ✅ |

T-ST-04 的 `explanation` 条数实测：`lr_v1` **10/14**、`rf_v1` 14/14、`xgb_v1` 14/14。

## 3. 两条断言口径（写清楚，免得被当成缺陷或当成造假）

1. **`explanation` 是"非零贡献"列表，条数 ≤ 14 是契约合规的。** `backend/app/model_registry.py` 的 `explain()` 末尾有 `if value != 0`：贡献恰为 0 的特征不进列表。契约三（`docs/backend/api-spec.md` §三.2/§三.4）只固定条目结构 `{feature, contribution, direction}` 与 **`features` 必须 14 键**，没有要求 `explanation` 满 14 条；`backend/tests/test_model_registry.py` 的断言也是"键名 ∈ 14 特征"。线性模型 `lr_v1` 在该提交上有 4 个特征的 SHAP 贡献精确为 0（系数或偏差为零），故 10 条；树模型极少出现精确零，故 14 条。**我的第一版断言写成"14 条全非零"，是断言越界而不是后端缺陷**，已改为"非空 + 键名 ⊆ 14 + 无重复"，此处留痕。
2. **清单外 5 个返回 `40001` 是预期行为，不是失败。** `backend/app/api/predict.py:86-88`：`model_name` 不在已加载清单 → 40001「参数非法：model_name 不在已加载模型清单」；在线清单 = `feature_order.txt` 的 `[models]` 段（#96/#98 + 冻结规格 `model-coverage` R6）。Issue #130 第二条裁定已把 T-ST-04 判据改成清单内外分判，本表按新判据执行。

## 4. 未覆盖（如实登记，不冒充）

- **页面半边**：T-ST-02 的页面提示与"不给重试"、T-ST-03 的空态渲染、T-ST-04 的下拉 8 项与 `[models]` 同步 —— 前端线（刘帅华），需起 `npm run dev` 后取证。
- **录屏**：T-ST-01~05 全链路录屏需前端 + 后端 + 模型三线同场（组长排期，下次课前一晚）。
- **T-ST-05 的"新增模型不破坏既有四接口"**：当前以「`openapi.json` 路径仍 4 条 + 错误码集合不变 + 幂等不变」作回归判据；真正的"新增模型进清单后回归"要等 change `online-eight-model-selection` 的 1.1 裁决（我在 #134 的实测意见：`et_v1` 稳态 SHAP ~1.78s 会破 500ms 靶子、`lgbm_v1` 的空归因是 `_is_tree_family` 不认 lightgbm 的一行缺陷）。
- **MySQL 侧**：本记录全程 SQLite。两条授权 Issue **并列、别混**（原文这里只写了 #121，是错号，按 #141 审阅条件 3 订正）：**演示库** `jit_demo` 的建库与授权在 **Issue #142**（sober-hub）—— 本记录要在 MySQL 上复跑回填，等的是这条；**#121** 是后端**真库验收**用的两个探针库 `jit_schema_probe` / `jit_orm_probe`（`acceptance.md` 第 1/6 条），照 #121 执行**不会产生演示库**。另：`jit_defect` 里现存的 2 提交 / 4 预测是占位脏数据（假哈希、`repo_name=activemq`、`smoke_v1`/`tree_placeholder_v0`），按演示脚本 §5 第 4 条不能上台，其存量处置归 infra，本线不动别人的库。

## 5. 复现

- 驱动脚本（建库 + 核对 + 起服务 + 43 项断言，任一步不符即退出码 1 并打印实际值）目前在本机临时目录，**不会留在那里**：按 #141 审阅条件 2 与 Issue #130 三，它并进 **Issue #138 的 `backend/scripts/demo_preflight.py`**（同一件事：录屏前一条命令自检、不静默通过、不拿跳过当绿，口径同 `security_cases.py`），含测试另开 PR。原文我提的 `system_cases.py` 这个文件名作废，以 #138 为准。
- 关键命令见 §1 与 §2 表格；服务起法 `cd backend && DATABASE_URL=sqlite:///…/demo.db API_TOKEN=*** MODEL_DIR=<交付包目录> python -m uvicorn app.main:app --port 8044`。
- 原始日志：本机 `driver.log` / `uvicorn.log`（含 43 行 PASS 与每模型的 `explanation` 条数），不入库。
## 6. 补记（2026-10-25，均为追加，不改写上文任何数字）

### 6.1 labels / features 的行数为什么会与交付包对不上（对账）

组长本机按交付包（`deliver_data_20261024.zip`）灌出 **labels 83,887 / features 84,461**，本记录与 `integration-2026-10-24.md` §2 记的是 **83,943×3**。差异不在灌库脚本，而在**两份 CSV 的口径不同**。下面是本机实测行数（`csv.reader` 逐行数，不取 `wc -l` 以免被引号内换行骗）：

| 文件 | 行数 | 是什么 |
|---|---|---|
| `data_model/data/commits.csv` | **84,461** | 全量提交（两边一致） |
| `data_model/data/commit_features_raw.csv` | **84,461** | **每个提交一行**的特征原始导出 —— 交付包里那份 features 就是它，故灌出 84,461 |
| `data_model/data/dataset_szz.csv` | 83,943 | 建模数据集（切分 58,760 + 25,183 = 83,943） |
| `data_model/data/commit_labels_szz.csv`（10-24 15:26 那次 02 独立重跑的产物） | **83,943** | 打标结果；本记录灌库用的是它的投影，且已与该次重跑**逐行核对一致**（见 `integration-2026-10-24.md` 的交叉校验补记） |
| 本记录灌库用的 `commit_features_for_ingest.csv` | 83,943 | `dataset_szz.csv` 的投影（只留数据集内的提交） |

- **features 84,461 vs 83,943 是超集关系，不是缺数**：raw 导出覆盖全部提交，投影只留数据集内的 83,943 行。
- **labels 83,887 比本机 `commit_labels_szz.csv`（83,943）少 56 行 —— 这一条我无法在本机证实来源**：交付包不在我机器上（全盘搜过没有该 zip），所以不猜。定位只需一条：把包内 labels CSV 的 `commit_hash` 集合与 `data_model/data/commit_labels_szz.csv` 做双向差集；若差集非空，说明包内那份来自**另一次打标运行**，以哪份为准属模型线口径（与 `dataset_szz.csv` 的 83,943、正样本 18,662 及切分/训练绑定的是 10-24 15:26 那一版）。
- **对演示与四接口的影响：不阻塞，但两张表性质不同，别混为一谈**：
  - `commit_label` **没有任何接口读它**（grep 实证：只有 `app/ingest.py` 写、`app/models.py` 定义），少 56 行不影响任何页面与断言；
  - `commit_feature` **是被读的**（详情返回 `features` 14 键；`POST /api/predict` 用它按契约二 §3 的列序组装 14 维向量），84,461 是 83,943 的超集，只会更宽松；
  - 真正必须守的不变式是「**有预测的提交必须有特征行**」（否则详情回 `features: null`、`POST /api/predict` 回 40400）。本记录那份库实测 **0 例外**，另两条（有预测必有 `commit` 行、有预测必有 `commit_label` 行）同样 **0 例外**；`commit_feature` 覆盖 83,943 个不同哈希。列表 `total` 由 `prediction` 与 `commit` 的内连接决定，两边都是 83,943，故演示口径一致。
  - 复核命令（SQLite 写法；MySQL 下同语义）：`select count(*) from prediction p left join commit_feature f using(commit_hash) where f.commit_hash is null` → 期望 0。

### 6.2 §1 复跑命令的口径订正（#145 复审意见落地）

原 §1 新段写的是「上面五条命令**一条不改**，只把 `DATABASE_URL` 换成 `mysql+pymysql://…`」，同时又说「口令走 `backend/.env`」。@sober-hub 复审指出这两句**互相冲突且不可执行**：五条命令都带行内 `DATABASE_URL=…` 前缀，而 `app/config.py` 的 `load_dotenv()` **不覆盖已存在的环境变量**，因此 `.env` 里的真实连接串不会生效，照占位符跑也连不上 MySQL。已按其改法订正为「**连接串写 `.env` + 五条命令去掉行内前缀**」，CSV 路径改为引用 `demo-script-sprint1.md` §0.0/§0.0.1 的唯一口径。原 SQLite 记录与「未在 MySQL 验证」的警示一律保留。

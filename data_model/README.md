# data_model/ — 数据与模型线

**负责人**：蒋励

## 职责

拉取并固定 ActiveMQ 仓库版本 → SZZ 打标（标准行级 + 文件级简化版，两套自研实现对照）→ 抽取 Kamei 14 项特征 → 训练 2–3 个经典模型 → 评估。

## 交付物

带标记的样本集、特征表、模型文件、评估报告。

## 目录结构（按这个放，不要新建同级目录）

| 路径 | 放什么 | 入库？ |
|---|---|---|
| `data_model/data/` | ActiveMQ 仓库副本、中间数据、样本集 | ❌ 被 `.gitignore` 排除 |
| `data_model/models/` | 训练出的模型文件（`.pkl` / `.joblib`） | ❌ 被排除 |
| `data_model/reports/` | 小体积统计结果、指标表、评估报告 | ✅ **可入库** —— 这是给别人比对的证据 |
| `data_model/artifacts/` | 中间产物、缓存 | ❌ 被排除 |

**脚本命名**：`01_xxx.py` / `02_xxx.py`（`0X` 前缀就是执行顺序），跑通后在 `docs/data-pipeline.md` 第 4 节回填路径。

**不要为了提交数据去改 `.gitignore`，也不要用 `git add -f`。**

## 依赖

```bash
pip install -r data_model/requirements.txt
```

## 链路（五步，顺序固定）

完整规则见 `docs/data-pipeline.md` —— **版本固定方式与复现命令都在那里，动手前先读**。

| 步 | 做什么 | 脚本 | 输出 |
|---|---|---|---|
| ① | 克隆 + checkout 到固定版本 | 手工执行（命令见 `docs/data-pipeline.md` 第 2 节） | `data/activemq/` |
| ② | 读提交记录（GitPython），过滤合并提交 | `01_extract_commits.py` | `data/commits.csv` |
| ③ | SZZ 打标 | `02_szz_labeling.py` | `data/commit_labels_{szz,szz_lite}.csv` |
| ④ | 算 Kamei 14 项特征 | `03_extract_features.py` | `data/commit_features.csv` + `reports/feature_stats.md` |
| ⑤ | 汇总成可训练样本集 + 打印统计 | `04_build_dataset.py` | `data/dataset_{szz,szz_lite}.csv` + `reports/dataset_stats.md` |

复现命令（含「先跑窗口子集验证链路」的短路径）见 `docs/data-pipeline.md` 第 5 节。

②③④ 的字段口径以契约为准，不要自己发明列名：`docs/contracts/data-fields.md`、`docs/contracts/feature-columns.md`。

## 四条铁规矩

1. **训练集/检验集按 `committed_at` 时间序切**（前 70% 训练、后 30% 检验），**禁止随机切分**。`EXP`、`NUC` 等特征与时间相关，随机切分等于让模型提前看到未来，测出的准确率是假的。
2. **特征列名与取值口径以 `docs/contracts/feature-columns.md` 为准**（v1.0 已冻结，`feature_version = v1`）：归一化分母、log 变换、熵的两周窗口都照契约，**不要自己改口径** —— 口径一改要全量重算，且与已有特征表对不上。
3. **数据集与模型文件一律不入库**（课程硬要求）。
4. 只在本目录内写代码：**不写接口、不写页面、不建库表**。方案 C 的交付物是一份 `prediction_result.csv`（字段对应契约一表三），**由后端线导入 `prediction` 表** —— 本线不直连数据库。表结构仍以 `docs/contracts/data-fields.md` 为准，本线不改、也不跑建表脚本。

## 「可复现」的最低要求

别人在你机器之外跑，要能拿到同一份结果。交付时必须能出示三样：

- 数据固定在哪个 tag / commit —— 回填进 `docs/data-pipeline.md` 第 2 节
- `reports/` 下的统计表：总提交数、正样本数、负样本数、**正样本比例**、打标方法
- 一条「从干净 clone 到出结果」的命令序列

**正样本比例是判断数据可用的第一个信号。** JIT 数据集通常很低（个位数到十几百分点），若算出来接近 50%，先查打标逻辑，不要往下走。

## 与后端线的对接（2026-09-16 已定：方案 A + C，不再是待定项）

`docs/contracts/data-fields.md` 已定 `commit_hash` 是对接主键、**四张表**的字段。**模型怎么交到后端**的三个候选，裁定如下：

| 方案 | 裁定 | 理由 / 用在哪 |
|---|---|---|
| **A. 后端加载模型文件** | ✅ **采用** | 后端启动时从 `data_model/models/` 加载 `.pkl`，供 `POST /api/predict` 实时推理 |
| **B. 后端调推理脚本** | ❌ 不采用 | 每次预测起一个 Python 进程，光解释器启动就几百毫秒，**过不了契约「95% 的请求 < 500ms」** |
| **C. 离线预测结果入库** | ✅ **采用** | 数据线离线全量预测并产出 `prediction_result.csv`，**由后端线导入 `prediction` 表**，供风险列表 / 提交详情 / 趋势看板三个查询接口读 |

**为什么 A 和 C 都要**：11,050 条提交不可能每翻一页都实时推理 —— 三个页面必须读预置结果（C）；而课程《项目要求》第 1 页要求「对外提供在线预测服务」，新提交进来要能立刻出概率，这只能靠实时推理（A）。**两者写同一张 `prediction` 表，靠 `model_name` 区分。**

**C 单独用不成立**：只读历史结果满足不了「在线预测服务」这条课程要求。（注意：容器化部署在课程里是**可选**，而在线预测服务是任务描述正文 —— 两者约束力不同，不要混为一谈。）

### 模型线要交出什么（方案 A 的接口）

| 项 | 内容 |
|---|---|
| 模型文件 | `data_model/models/` 下的 `.pkl` / `.joblib`，文件名含版本号（如 `xgb_v1.pkl`）。**该目录被 `.gitignore` 排除** —— 交付走打包或网盘，不提交进仓库 |
| 特征顺序 | **以 `docs/contracts/feature-columns.md` 的列序为唯一来源**，不另发一份清单 —— 出两份早晚会不一致，而顺序错了模型不报错、只会静默给出错误答案 |
| 版本标识 | `model_name` 取值（如 `xgb_v1`），与 `prediction.model_name`、接口入参同名 |
| 加载说明 | 模型类型（sklearn / XGBoost）、依赖与版本，写进 `reports/` 的评估报告 |
| SHAP 解释器 | 模型类型要能对应到 SHAP Explainer（树模型用 `TreeExplainer`）—— 契约已定 `explanation` 由 SHAP 产出，故 `shap` 是本线依赖 |

> 模型文件不入库，所以「别人 clone 后能否复现」靠的是**能重新训出同一个模型**：固定数据版本 + 固定特征口径 + 固定随机种子。这也是本线「可复现」三样证据之外的第四样。

# 模型训练与交付

> Sprint 0 ｜ 对应飞书《工作周报-任务号待对飞书周报回填》
> 起草 2026-09-16 ｜ 起草人 蒋励 ｜ 关联契约：`docs/contracts/feature-columns.md`（v1.0 冻结）、`data-fields.md`（表三 `prediction`）、`api-format.md`
>
> ⚠️ **契约基线以「合并后的 `main`」为准。** 上述冻结版本目前分别待在 PR #5（`docs/contracts/feature-columns-v1`，契约二 v1.0）与 PR #6（`docs/docs/freeze-contracts-v1`，契约一 1.2 / 契约三 1.2）上，**尚未进 `main`**。本 change 的规格锚定的是这两个 PR 合并后的状态；若它们的内容再有变动，本 change 的 spec 需同步。这条依赖同时登记在 `design.md` 的 Risks 一节。

## Why

样本集已全量产出（11,050 条非合并提交，`szz` 正样本比例 38.98%），链路却停在「可训练」这一步：`data_model/` 下没有任何训练脚本，后端线等不到 `.pkl` 与预测结果，前端三个页面全部空转。同时交付方式已在两线间裁定为 **A+C**（后端加载 `.pkl` 实时推理 + 数据线离线全量预测入库，靠 `model_name` 区分来源），这个跨线决定必须落进规格，不能只活在聊天记录里。

本 change 还清两笔欠账：

1. **特征计算的规格欠账**：`03_extract_features.py` 已全量跑完（`reports/feature_stats.md`），但首个 change 的 proposal 当初把特征计算显式划出（「另开 change」），那个 change 至今没建 —— 代码先行、规格缺位，按 AGENTS.md 红线第 2 条属现存缺陷，本 change 补登记。
2. **交付方式的规格空白**：A+C 中 C 方案在 `data_model/README.md` 末节写的是「模型线批量预测写 prediction 表」，与该文件铁规矩 4「不建库表」及 `docs/sprint0-scope.md` 第 3 节数据线边界（不碰库表）**直接冲突**。本 change 显式裁定（见 What Changes 第 3 条）并修正该表述。

## What Changes

- **新增「特征抽取」能力登记**：把已实现的 `03_extract_features.py` 与既有产物（`reports/feature_stats.md`）登记为 spec capability `feature-extraction`，口径对齐契约二 v1.0（`rexp` 衰减公式、六项 DECIMAL、`ln` 0 点不连续的 v1 已知局限、`nuc` 按文件计数求和）。**不是新代码，是补规格欠账**
- **新增「模型训练」能力**：按 `committed_at` 时间序切分（前 70% 训练 / 后 30% 检验，**禁止随机切分**，AGENTS.md 红线第 1 条）；脚本内置断言「检验集最早 `committed_at` > 训练集最晚 `committed_at`」，违反即失败退出；训练 2–3 个经典模型（LR / RF / XGBoost 量级）；产出 Effort-unaware（AUC / F1 / 精确率召回率）与 Effort-aware 两类指标，落 `data_model/reports/`
- **裁定一（跨线）——C 方案灌库责任**：**数据线只产出结果文件，不碰数据库**。数据线产出 `prediction_result.csv`（字段与契约一表三一一对应：`commit_hash` / `model_name` / `risk_score` / `predicted_at` / `feature_version`），由**后端线**灌入 `prediction` 表。同步修正 `data_model/README.md` 末节 C 方案那句「模型线批量预测写 prediction 表」
- **裁定二——主训练标签**：主模型用 `szz`（自研标准行级 SZZ）训练。理由：与 Kamei 原文口径可比（`sprint0-scope.md` 第 2 节：结果要与文献对比才有说服力）；`szz_lite` 粒度粗（正样本比例 27.74% vs 38.98%），定位为**对照校验工具**，不入主模型
- **新增「模型交付」能力**：`.pkl` 导出至 `data_model/models/`（已被 `.gitignore` 排除，不入库），随包交付特征顺序清单（按契约二第三节 v1.0 列序）；`model_name` 命名规则 `<算法>_v<序号>`（如 `xgb_v1`，与契约一表三示例一致），迭代换名不覆盖；SHAP 作为解释算法（定稿后回填契约三「待确认」项），SHAP 实时计算需过后端非功能要求验证（95% 请求 < 500ms）
- **文档回填**：`data_model/README.md` 末节从「三个候选待定」改为已定 A+C；`docs/data-pipeline.md` 链路表补训练 / 导出 / 全量预测步骤
- **新增依赖（显式登记）**：`scikit-learn`、`xgboost`、`shap`（及随带 `joblib`）进 `data_model/requirements.txt`，版本钉死

**前提声明**：课程《项目要求》原文要求「至少 2 类（经典机器学习和深度学习）不少于 8 种预测模型」，本组按 MVP 先做 2–3 个经典模型、不做深度学习，**分期口径待老师确认**（飞书周报任务 12，9/16 约谈议题）。若老师不同意分期，本 change 的工作量需重新估算。

**不做什么（显式列出）**

- **不做** 深度学习模型、不做 8 种模型全量实现 —— 前提见上，重开条件见 `sprint0-scope.md` 第 2 节
- **不做** 数据线直连数据库写入 `prediction` 表 —— 裁定一已明确灌库责任在后端线
- **不做** `szz_lite` 主模型 —— 裁定二已明确其定位为对照校验
- **不做** 超参调优的自动化搜索（网格/贝叶斯） —— 经典默认参数 + 少量手动调整即可，课程周期内以跑通为先
- **不改** 三条契约的字段名、列名、接口路径 —— 契约已冻结（契约二 v1.0），只在实现层遵守；**契约三「待确认」一节已由 PR #6 结清**（`explanation` 的具体算法已定为 SHAP），故本 change **不再有「SHAP 定稿后回填契约」这一动作**，也不动契约正文格式
- **不做** CI 强制拦截、不做容器化部署 —— 系统定位与范围文档已有结论

**是否触及 `docs/sprint0-scope.md` 的边界**：**不触及**。训练 2–3 个经典模型与两类评估指标本就在该文第 2 节「做」清单内；裁定一不是边界变更，而是**修正 README 末节与既有边界（数据线不碰库表）冲突的一句表述**，边界本身不变。

## Capabilities

### New Capabilities

- `feature-extraction`: 从样本集算 Kamei 14 项特征，列名与取值口径照契约二 v1.0，历史类特征用完整历史，产出特征表与 `feature_stats` 报告（登记已实现内容）
- `model-training`: 按 `committed_at` 时间序切分训练/检验集，训练 2–3 个经典模型，产出 Effort-unaware 与 Effort-aware 两类评估指标
- `model-delivery`: 导出 `.pkl` 与特征顺序清单，按 `<算法>_v<序号>` 规则命名，产出全量预测结果文件（C 方案交付物），登记 SHAP 依赖与版本

### Modified Capabilities

无 —— `openspec/specs/` 主规范仍为空（首个 change 尚未归档），没有被修改的既有能力。

## Impact

| 项 | 内容 |
|---|---|
| 影响目录 | `data_model/`（新增训练/导出/预测脚本与产物）、`docs/data-pipeline.md`（链路表补步骤）、`data_model/README.md`（末节裁定回填）、`data_model/requirements.txt`（新增三个依赖） |
| 消费的契约 | `feature-columns.md` v1.0（特征列序与口径）、`data-fields.md` 表三 `prediction`（结果文件字段）、`api-format.md`（SHAP 回填「待确认」项）—— 只读不改 |
| 新增依赖 | `scikit-learn` / `xgboost` / `shap`（版本钉死进 `requirements.txt`） |
| 交付给后端线 | A：`.pkl` 文件路径 + 特征顺序清单 + SHAP 依赖及版本 pin；C：`prediction_result.csv`（后端负责灌 `prediction` 表） |
| 数据边界 | `.pkl`、数据集、中间产物一律不入库；只把 `reports/` 下的小体积评估报告入库当证据 |
| 下游依赖 | 后端模型加载与 predict 接口、前端三个页面的数据内容，均等本 change 交付 |

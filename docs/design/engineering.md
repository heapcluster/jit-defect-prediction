# 工程化模块设计（分支规范 / 代码评审 / CI-CD / 插件化）

> 模块归属：课程《项目要求》「工程化（Git 分支规范 + 代码评审；CI/CD 流水线、插件化等）」
> 负责线：**苏哲勋（工程化 / infra）** ｜ 审核：蒋励 ｜ 关联：`repo/collaboration.md`、`repo/git-pr.md`、`docs/design/architecture.md`
> 本文把「工程化」从一句责任描述补齐为**可落地的设计**，对应课程硬要求里的工程化模块。

---

## 0. 👤 这个模块谁负责

| 子项 | 负责 | 细则落点 |
|---|---|---|
| 分支规范 | 苏哲勋 | `repo/collaboration.md` §分支模型 |
| 代码评审 | 全员（PR 非作者审阅） | `repo/collaboration.md` §3 |
| CI/CD 流水线 | 苏哲勋 | **本文 §3** |
| 插件化架构 | 苏哲勋（接口） + 吕建江（后端落地） + 蒋励（模型实现） | **本文 §4** |

> 其余三人按各自包接入本模块：后端遵循插件化接口、模型线按注册表接实现、前端走同一 CI。

## 1. 工程化 ↔ 课程要求 对应

| 课程《项目要求》原文 | 本项目落地 |
|---|---|
| Git 分支规范 | `repo/collaboration.md` §分支模型（`main`/`develop`/`feature/*`/`change/*`） |
| 代码评审 | PR 合并前 ≥1 位非作者审阅，意见留 Git（`repo/collaboration.md` §3） |
| CI/CD 流水线 | **本文 §3**（GitHub Actions：lint→test→build→(可选)deploy） |
| 插件化 | **本文 §4**（Predictor 注册表 + 特征/数据集插件） |

## 2. 分支规范（速览，细则在协作文档）

- `main`：可发布基线，只接收已审阅且 CI 通过的 PR。
- `develop`：集成分支，各 `feature/*` 汇入。
- `feature/*`：功能开发分支。
- `change/*`：OpenSpec change 实现分支（规格 propose→apply→tasks→代码→archive）。
- 文档线 PR 走 `docs/README.md` §0 强制合入规则（蒋励主笔，GitHub 账号 `jolly326`，sober 无条件合入）。

## 3. CI/CD 流水线设计

**目标**：PR 提交即自动构建与测试，为「软件开发过程实践 40 分」提供自动化证据，并满足「配置自动化流水线 CI/CD，在提交或 PR 时执行构建和自动化测试」（Sprint 1 可选项，本组落地）。

- **触发**：push / PR 到 `main`、`develop`，以及 `change/*`。
- **阶段（门禁顺序）**：
  1. `lint`：`ruff`/`flake8`（Python）、`eslint`（前端）—— 风格与静态检查。
  2. `unit-test`：各线单测——后端四接口与鉴权（`backend/tests/`）、模型加载（`joblib.load` 口径）与 SHAP 解释（`backend/tests/test_model_registry.py`）、14 特征口径（`data_model/tests/test_feature_contract.py`）、前端口径函数（`frontend/` 执行 `npm run test:unit`，vitest）。
  3. `build`：`docker build` 后端镜像；前端 `vite build`。
  4. `(可选) deploy`：Sprint 1 起接容器化公网访问（课程标可选）。
- **门禁**：CI 红 = 禁止合入；**PR 仍需 ≥1 位非作者人工审阅**（自动化不替代评审，呼应协作规则）。
- **产物**：测试报告、覆盖率、`docker` 镜像、`build` 产物。
- **位置**：`.github/workflows/ci.yml`。

## 4. 插件化架构

**目标**：满足「≥2 类（经典机器学习 + 深度学习）不少于 8 种预测模型」，且**新增 / 淘汰模型零改核心路由与库表**。

### 4.1 模型插件（Predictor 注册表）

- 抽象接口 `Predictor`：`load() -> self` / `predict(features: dict) -> float` / `explain(features) -> list[SHAP]`。
- 注册表：`MODEL_REGISTRY: dict[str, Type[Predictor]]`，键为 `model_name`。
- 8 种实现：经典 6（`lr` `rf` `xgb` `lgbm` `et` `svm`）+ 神经网络 2（`mlp_deep` `tabnet`），各实现同一接口（清单见 `model/model-line-plan.md` §2.1）。
- 后端按 `model_name` 从注册表加载，对应 `prediction` 表复合主键 `(commit_hash, model_name)`——**新增模型只加注册项，不改 `api-spec` 与库表**。
- 落点：`backend/app/model_registry.py`（接口 + 注册表 + 8 实现）。

### 4.2 特征提取器插件

- `FeatureExtractor` 接口：`extract(commit) -> dict[14 项]`。
- 必做：经典 Kamei 14（`feature-columns.md` 口径）。
- 可选：代码语义特征（G1-4，语义嵌入插件；详设见 `addons.md` §4）。

### 4.3 数据集插件

- `RepoSource` 接口：克隆 / 解析提交 / 产出样本。当前 `Apache Camel`（锁 `camel-4.23.0`）；新增仓库 / 公开 JIT 数据集（G1-3）只实现同一数据源接口，不动管线（详设见 `addons.md` §3）。

### 4.4 收益

- 模型扩展/淘汰不影响路由、库表、前端——呼应课程「插件化」要求，也为「插件化嵌入代码平台」可选项预留接口。

## 5. 评分映射（本模块贡献）

| 评分维度 | 分值 | 本模块证据 |
|---|---|---|
| 软件开发过程实践 | 40 | Git 分支/PR/看板/CI 自动化（本模块）+ 各 Sprint 完成度 |
| 生成式软件开发（SDD） | 10 | change 链路完整 + CI 门禁 |
| 软件测试实践 | 40 | CI 跑 `pytest` 单测即测试自动化证据 |

## 6. 本模块下一步（Sprint 归属）

| # | 事项 | 何时 | 负责 |
|---|---|---|---|
| E1 | 落 `.github/workflows/ci.yml`（lint→test→build） | Sprint 1 起 | 苏哲勋 |
| E2 | `backend/app/model_registry.py` 落地 Predictor 接口 + 8 实现 | Sprint 0–1 | 吕建江 + 蒋励 |
| E3 | 插件化 non-functional 证据（新增模型回归不破接口） | Sprint 2–3 | 苏哲勋 |
| E4 | （可选）容器化 deploy 阶段 | Sprint 1 起可选 | 苏哲勋 |

> 注：CI/CD、容器化、插件化嵌入代码平台在课程《项目要求》中标注为「可选 / Sprint 1 起可接」；本组选择**落地 CI/CD 与模型插件化**作为工程化亮点，容器化 deploy 按需开启。

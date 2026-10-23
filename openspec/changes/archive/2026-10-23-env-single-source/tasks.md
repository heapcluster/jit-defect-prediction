# env-single-source — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/environment/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-10-21 ｜ 状态：已完成（8/8 任务勾选，2026-10-23 归档；§3 验收 ③ Linux/WSL、④ GPU 两条**未执行**，已在 §5 已知缺口登记，不计入完成范围）
> 用户故事：无（工程化）
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. 环境文件收敛

- [x] 1.1 `git mv environment.yml data_model/environment.yml` — 唯一权威文件归位
- [x] 1.2 删除 6 个 `requirements.txt`（`backend/`、`data_model/`、4 个 pipeline）— `git rm`
- [x] 1.3 版本对齐 + 去 `prefix` + 去 win-64 build — `data_model/environment.yml`

## 2. 文档同步

- [x] 2.1 更新安装命令：`README.md`、`data_model/README.md`、`backend/README.md`、`docs/common/dev-handbook.md`、`docs/repo/demo-script-sprint1.md`
- [x] 2.2 更新路径引用：`docs/model/explanation.md`、`docs/model/data-pipeline.md`、`docs/model/model-line-execution-plan.md`、`data_model/pipelines/README.md`、`data_model/pipelines/e2e/README.md`、`data_model/pipelines/expert/model.py`
- [x] 2.3 更新活规格：`openspec/specs/model-delivery/spec.md`、`openspec/specs/db-schema/spec.md`
- [x] 2.4 新增 `data_model/ENVIRONMENT.md`：另一台电脑开箱即用（CUDA torch / 数据获取 / 四线训练 / 报告入库 / 模型交付）；并从 `data_model/README.md` 链接
- [x] 2.5 修正 `.gitignore`：任意 pipeline `models/**` 权重（含 HF `*.safetensors` / `*.bin`）忽略，保留 `feature_order.txt` / `manifest.txt` 交付清单

> 验证记录（2026-10-22）：
> 1. `data_model/environment.yml` YAML 解析通过（`name=jit-defect-prediction`，26 个 pip 包）。
> 2. `conda env create --dry-run -f data_model/environment.yml` **求解成功**，依赖无冲突（`evidence/env-create-dryrun.txt`）。
> 3. **真实创建通过**：`conda env create -f data_model/environment.yml -n jit-defect-prediction-verify -y`（团队已有同名环境在用，仅改环境名避免覆盖，包集合一致）→ Python 3.12.15 / torch 2.5.1+cpu / transformers 4.46.1，26 个 pip 包全部装上（`evidence/env-create-verify.txt` + 原始日志 `env-create-verify-log.txt`）。
> 4. **依赖导入通过**：`import torch, transformers, pandas, numpy, sklearn, xgboost, lightgbm, matplotlib, accelerate, pytorch_tabnet, git, joblib` → `all imports OK`。
> 5. **测试通过**：`python -m pytest data_model/tests backend/tests -o addopts="" -q` → **197 passed**（32.19s，退出码 0）。
> 6. `git grep` 确认无安装步骤指向已删的 `requirements.txt`（命中仅为说明性文字与历史证据）。
>
> 仍未覆盖：CUDA（本环境为 CPU 轮子，cu124 二次安装与 `True` 断言需在 4060 上执行）、Linux/WSL 跨平台重复创建。

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`。铁律：**勾了 tasks ≠ 功能合格**。

### 1. 单元测试（本 change 无新增业务代码）

| 项 | 内容 |
|---|---|
| 覆盖对象 | 无新增函数；验证环境文件与文档引用一致性 |
| 测试文件 | 无需额外文件（纯 `git grep` 校验，避免依赖本地私有脚本） |
| 用例数与结果 | 0 条（无代码）/ — |
| 复现命令 | `git grep -n "requirements.txt" -- '*.md' ':(exclude)openspec/changes/archive'` |
| 正向用例 | `data_model/environment.yml` 可被 YAML 解析且 `name=jit-defect-prediction` → 通过；`conda env create --dry-run` 求解成功 → 通过 |
| 异常 / 边界用例 | 全仓库无指向已删 `requirements.txt` 的**安装步骤** → 期望 0 命中。实测命中可按 4 类归因：① `README.md` / `backend/README.md` / `data_model/ENVIRONMENT.md` / `docs/model/model-line-execution-plan.md` / `docs/repo/demo-script-sprint1.md` / `data_model/pipelines/e2e/README.md` 的“不再有 requirements.txt”说明；② `backend/scripts/evidence/*`（2026-10-16/17 历史证据）与 `docs/common/test-report-sprint1.md`（Sprint 1 历史报告）；③ 本 change 的 `proposal.md` / `design.md` / `spec.md` / `tasks.md` 自身。其中仅剩 3 处 `pip install -r backend/requirements.txt`，全部位于 2026-10-16/17 的历史证据文件（`backend/scripts/evidence/coverage-2026-10-16.md`、`coverage-2026-10-17.md`、`predict-real-models-2026-10-16.md`），属当次运行快照，按 `design.md` D3 保留原样、不再可执行；现行文档与安装步骤 0 命中 |

### 2. 集成测试（大版本合并后）

| 项 | 内容 |
|---|---|
| 集成范围 | 环境创建 + 现有 197 项测试不因依赖缺失而失败 |
| 测试文件 | `backend/tests/`、`data_model/tests/` |
| 用例数与结果 | **通过**：新环境 `python -m pytest data_model/tests backend/tests -o addopts="" -q` → **197 passed**（32.19s，退出码 0） |
| 复现命令 | `conda env create -f data_model/environment.yml && conda activate jit-defect-prediction && python -m pytest data_model/tests backend/tests -q` |
| 关键断言 | 环境创建成功；pytest 全绿（本次 197 passed，含 data_model 97 + backend 100） |

### 3. 验收测试（交付时）

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/environment/spec.md` 的 4 个 Scenario |
| 用例数与结果 | 4 条：① 建环境 **通过**（win-64 真实创建，197 passed）② 无重复清单 **通过**（`git grep`）③ 跨平台 **待执行** ④ GPU 校验 **待执行** |
| 复现命令 / 步骤 | ① `conda env create -f data_model/environment.yml` ② `git grep -n "requirements.txt"` ③ Linux/WSL 上重复 ① ④ `python -c "import torch; print(torch.cuda.is_available())"` |
| 各项判据 | ① 创建结束无 error 且 `conda env list` 出现该环境；② 无安装命令指向现存 `requirements.txt`；③ Linux/WSL 上 ① 同样通过；④ 4060 上输出 `True` |
| 证据归档 | `evidence/env-create-dryrun.txt`、`evidence/env-create-verify.txt`（+ `env-create-verify-log.txt`）+ 本 `tasks.md` + PR 描述 |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | 不涉及运行时 |
| 安全 | 否 | 无密钥入库 |
| 可靠 | 是 | 去 `prefix` / win build，跨平台可复现 |
| 易用 | 是 | 单文件安装 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| CUDA 未实测 | 本次创建装的是 PyPI CPU 轮子；cu124 二次安装与 `True` 断言需在 RTX 4060 上执行 | model 蒋励 | 在 GPU 训练机执行 §3 ④ 后回填 |
| Linux/WSL 未实测 | 只在 win-64 完成创建与测试 | model 蒋励 | 在 WSL 执行 §3 ③ 后回填 |
| CI 未覆盖环境创建 | 环境创建耗时且依赖缓存，当前 CI 不跑 | model 蒋励 | 如需常驻保障，后续加定时任务 |
| CUDA 版 torch 需创建后二次安装 | `environment.yml` 无法按包指定 index-url | model 蒋励 | 已写入文件头与 e2e README |

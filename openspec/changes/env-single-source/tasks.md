# env-single-source — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/environment/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-10-21 ｜ 状态：进行中
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

> 验证记录（2026-10-21，本机）：`data_model/environment.yml` YAML 解析通过（name=jit-defect-prediction，26 pip 包）；全仓库无 `data_model/requirements.txt` 活引用；`check_links.py` 对 `data_model/environment.yml` 全部 OK。`check_links` 报的 11 个 BROKEN 均为四包拆分前遗留的陈旧路径（`06_train_model.py`、计划中的 `10~16_*.py` 等），**非本 change 引入**，另记后续清理。

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`。铁律：**勾了 tasks ≠ 功能合格**。

### 1. 单元测试（本 change 无新增业务代码）

| 项 | 内容 |
|---|---|
| 覆盖对象 | 无新增函数；验证环境文件与文档引用一致性 |
| 测试文件 | `tools/check_links.py`（本地工具，已 gitignore） |
| 用例数与结果 | 0 条（无代码）/ — |
| 复现命令 | `python tools/check_links.py README.md data_model/README.md docs/model/explanation.md docs/model/data-pipeline.md` |
| 正向用例 | `data_model/environment.yml` 可被 YAML 解析且 `name=jit-defect-prediction` → 通过 |
| 异常 / 边界用例 | 全仓库 grep 无残留 `data_model/requirements.txt` 活引用 → 期望 0 命中 |

### 2. 集成测试（大版本合并后）

| 项 | 内容 |
|---|---|
| 集成范围 | 环境创建 + 既有 146 测试基线不因依赖缺失而失败 |
| 测试文件 | `backend/tests/`、`data_model/tests/` |
| 用例数与结果 | 待换机后 `conda env create -f data_model/environment.yml && python -m pytest -q` |
| 复现命令 | `conda env create -f data_model/environment.yml && conda activate jit-defect-prediction && python -m pytest -q` |
| 关键断言 | 环境创建成功；pytest 全绿（基线 146 passed） |

### 3. 验收测试（交付时）

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/environment/spec.md` 的 Scenario |
| 用例数与结果 | 3 条（建环境 / 禁止残留 / 跨平台）｜ 待换机后执行 |
| 复现命令 / 步骤 | `conda env create -f data_model/environment.yml` |
| 证据归档 | 本 `tasks.md` + PR 描述 |

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
| 尚未在新 4060 机实跑 `conda env create` | 待换机 | model 蒋励 | 换机后首次开训前 |
| CUDA 版 torch 需手动二次安装 | `environment.yml` 无法按包指定 index-url | model 蒋励 | 已写入文件头与 e2e README |

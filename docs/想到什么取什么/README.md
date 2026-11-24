# 测试交付总体说明

## 0 重构期口径（2026-11-21 增补）

- **证据冻结**：本文及子目录的实测数字、通过率、覆盖率、截图与执行记录冻结于 `2734c1b`（2026-11-15 执行），不因重构改写或重新解释；重构后的复跑须另起执行记录并注明 SHA。
- **契约变更**：需求基线升级为 [`../../TODO/00-重构说明与开发执行要求.md`](../../TODO/00-重构说明与开发执行要求.md) 至 `TODO/09`（八模块可独立运行/配置/验收）；技术契约见改写后的 [`../README.md`](../README.md)、[`../database/README.md`](../database/README.md)。旧口径「固定流水线 + 只读展示 + 阈值写死 .env + 指标只读 CSV + 仅 expert 有 SHAP + 同步唯一计算入口」废止。
- **验收面增量（待新增用例、待执行）**：配置落库与重启恢复；收集任务五态 + 仓库可配 + CSV/XLSX 导出；清洗注册表 preview/apply 与前后统计图；训练多算法 + 超参表单 + 工件登记 + 热加载 + 失败隔离；批量/数据集预测；评估阈值/指标勾选/多模型对比（默认 0.5 与离线 CSV 逐值一致）；XAI 双技术（SHAP+LIME）与兼容矩阵；完整源码浏览 + 行级评分配置化；门禁默认建议/严格模式可配。
- **统计口径**：§2 用例总数与 §4 效果数字为冻结轮次口径；重构新增用例计入新一轮统计，MUST NOT 混入本轮数字。集成覆盖率分母「11 端点」同为冻结口径，重构后按运行时 `/openapi.json` 重算。
- **红线不变**：未实际执行的验收不得记通过；AI 生成用例须人工审核留痕；实测与预期不符如实报告。

## 1 项目概述

| 项 | 内容 |
|---|---|
| 系统名称 | 即时软件缺陷预测系统（Just-in-Time Defect Prediction） |
| 核心能力 | 以 Git commit 为单位预测缺陷风险，输出风险概率、归因解释与修复参考 |
| 技术栈 | 后端 Python 3.12 + FastAPI + SQLAlchemy + MySQL 8.0；前端 Vue 3 + Vite + Element Plus；模型 scikit-learn / XGBoost / LightGBM / PyTorch-TabNet / CodeBERT，四条模型线（expert / semantic / fused / e2e） |
| 数据源 | Apache Camel，固定 tag `camel-4.23.0`（commit `b2329103…`） |
| 测试框架 | pytest（后端、模型线、基础设施、CI 契约）、vitest（前端） |

## 2 各类测试用例总数及来源统计

| 测试类型 | 用例总数 | AI 生成 | AI 生成-人工修改 | 手写 |
|---|---:|---:|---:|---:|
| 单元测试 | 534 | 102 | 411 | 21 |
| 集成测试 | 35 | 35 | 0 | 0 |
| 系统测试 | 30 | 30 | 0 | 0 |
| 验收测试 | 20 | 20 | 0 | 0 |

单元测试来源按文件级标签归属汇总（57 个测试文件，每个文件头含考核说明 §2.1 格式的比例注释）。

## 3 使用的 AI 工具

| 工具 | 版本 | 用途 |
|---|---|---|
| CodeBuddy | DeepSeek-V4.1-Flash | 用例骨架生成、参数化数据构造、Mock 配置、覆盖率分析、文档整理 |

## 4 AI 辅助测试的整体说明

**使用环节**

- 单元测试：按模块生成用例骨架与参数化数据，核心业务断言（鉴权码、错误码、风险概率区间、14 维特征列序）由人工补充与复核。
- 集成测试：依据 `docs/api/` 契约生成 11 个端点的四类场景用例（正常 / 缺参 / 非法参数 / 边界）。
- 系统测试：生成功能与非功能用例初稿、性能脚本骨架、缺陷记录整理。
- 验收测试：依据需求条目生成验收用例初稿与 Scenario 对照。

**效果**

- 单元线 534 条全通过，行覆盖率 87%、分支 77%，其中 AI 生成 102 条、AI 生成后人工修改 411 条、纯手写 21 条，采纳率处于「有选择性采纳」区间。
- 集成线 35 条覆盖全部 11 个端点，34 条通过，1 条因图集产物缺失失败。
- 系统线 30 条覆盖功能、异常、边界与非功能四类，反向用例占比 62.5%。

**遇到的问题**

- AI 生成的断言偏向「接口返回 200 即通过」，需要人工改写为业务语义断言（如 `code==40100`、`0 <= risk_score <= 1`）。
- 部分模块的用例生成提示词未在生成当时归档，已按模块回溯补齐结构说明，见各测试类型的 `prompts/` 目录。
- AI 生成的测试计划与总结需人工复核并补充判断，不能直接作为交付结论。

## 5 运行说明

单元测试在各端真源目录执行：

```bash
# 后端
cd backend && python -m pytest -q --cov=app --cov-branch

# 模型线
cd data_model && python -m pytest -q

# 前端
cd frontend && npm run test:unit

# 基础设施与 CI 契约
python -m pytest -q infra/tests
python -m unittest discover -s .github/ci/tests -p 'test_*.py'
```

集成、系统与验收测试需先启动后端服务（`cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`），脚本在 `backend/scripts/` 下：

```bash
cd backend
python scripts/integration_cases.py        # 接口集成，35 条
python scripts/security_cases.py           # 安全，18 条
python scripts/system_exceptions.py --scenario all   # 系统异常，13 条
python scripts/online_models_matrix.py     # 25 模型在线矩阵
python scripts/perf_loop.py                # 单客户端性能
python scripts/load_test.py --users 20 --requests 10 # 并发负载
python scripts/linkage_capture.py          # 联调包络留痕
python scripts/acceptance_scenarios.py     # 验收可自动判定子集
```

一键复跑：`powershell -File backend/scripts/reproduce_all.ps1 -Sha <提交SHA>`（需服务已启动、`API_TOKEN` 已设置）。

各测试类型的详细报告、覆盖率与证据见对应子目录： [`unit_test/`](unit_test/README.md)、[`integration_test/`](integration_test/report.md)、[`system_test/`](system_test/test_plan.md)、[`acceptance_test/`](acceptance_test/acceptance_plan.md)。

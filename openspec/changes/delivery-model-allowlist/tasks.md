# delivery-model-allowlist — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/predict-api/spec.md`
> 负责人：backend 吕建江（PO 苏哲勋把关）｜ 创建：2026-10-23 ｜ 状态：进行中（实现与本地回归，待真实权重验收）
> 关联需求：当前在线交付八模型；本 change 只约束“按获批清单加载”，八项枚举与验收见 `online-eight-model-selection`
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 后端加载门禁

- [x] 1.1 按交付清单过滤模型并核对 14 项列序 — `backend/app/model_registry.py`，`python -m pytest -q backend/tests/test_model_registry.py` 中额外权重用例只载入清单模型。
- [x] 1.2 覆盖缺失/漂移清单的拒绝加载路径 — `backend/tests/test_model_registry.py`，同一测试命令验证注册表为空。

## 2. 跨线交付

- [ ] 2.1 模型线蒋励交付 `data_model/pipelines/expert/models/feature_order.txt` 与八款同名权重给 backend 吕建江 — 后端对照当前在线清单做 8/8 真实加载与预测取证，未取得可复核证据前不勾选。

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 清单解析、只加载声明权重、缺失/错序拒绝加载 |
| 测试文件 | `backend/tests/test_model_registry.py` |
| 用例数与结果 | 定向回归 16 passed，后端全套 102 passed；真实权重仍待验收 |
| 复现命令 | `cd backend && python -m pytest -q tests/test_model_registry.py` |
| 正向用例 | 历史合成用例为目录四权重、清单三模型 → 注册表仅三项；八模型现行清单须另验 |
| 异常 / 边界用例 | 无清单或列序被改 → 注册表为空 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 测试模型权重 → 加载器 → 预测接口；真实权重联调待交付 |
| 测试文件 | `backend/tests/test_predict_api.py` |
| 用例数与结果 | 定向回归 16 passed；真实权重未执行 |
| 复现命令 | `cd backend && python -m pytest -q tests/test_model_registry.py tests/test_predict_api.py` |
| 关键断言 | 已声明模型可预测；未声明模型不可用；无模型时 50000 不泄露路径 |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/predict-api/spec.md` 三个 Scenario |
| 用例数与结果 | 合成模型测试通过；真实八权重仍须按当前提交取证 |
| 复现命令 / 步骤 | `cd backend && python -m pytest -q tests/test_model_registry.py`；`openspec validate delivery-model-allowlist --strict --no-interactive` |
| 证据归档 | 旧证据已随 #187 删除；真实八模型验收证据待重建，不能视为已通过 |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是，未验收 | 需现行八权重逐项压测并提供可点证据；旧证据已删除 |
| 安全 | 是 | 清单模型名限安全文件名，错误不回显路径；`cd backend && python -m pytest -q tests/test_model_registry.py` |
| 可靠 | 是 | 缺清单/错序拒载、单个模型损坏可降级；同上 |
| 易用 | 否 | 前端本 change 不触及；`cd backend && python -m pytest -q tests/test_model_registry.py` 仅覆盖后端 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 真实八权重未在干净环境逐项复核 | `.pkl` 不入库，需模型线交付受控压缩包并留 8/8 证据 | model 蒋励 / backend 吕建江 | 联调交付时 |
| 预测 p95 未验证 | 本变更只限加载清单，不含在线特征现算优化 | backend 吕建江 | 单条特征接入 PR 时 |

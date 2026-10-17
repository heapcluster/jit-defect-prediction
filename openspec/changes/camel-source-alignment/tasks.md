# camel-source-alignment — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/commit-collection/spec.md`、`specs/szz-labeling/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-10-15 ｜ 状态：进行中（实现与回归完成，待审核及全量复现）
> 用户故事：沿用数据采集与 SZZ 打标；无新增用户故事
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 版本与实现
- [x] 1.1 核验官方 Camel tag 的完整提交 — `docs/model/data-pipeline.md` §2。
- [x] 1.2 修正报告判据、登记状态及不一致退出 — `data_model/preparation/02_szz_labeling.py`。

## 2. 文档与验证
- [x] 2.1 同步当前文档与活规格，注明历史报告勘误 — 数据链路、数据字段契约及两个规格。
- [x] 2.2 执行数据线回归与 OpenSpec 验证 — `data_model/preparation/reports/camel_source_alignment_validation.md`。

## 测试与验证（强制板块）

### 1. 单元测试
- 覆盖：Camel 判据、报告生成、自检基准与 CLI 提前失败；测试文件 `data_model/tests/test_szz_labeling.py`。
- 命令：在 `data_model/` 执行 `.venv/Scripts/python.exe -m pytest -o addopts='' -q -ra`。
- 正向：CAMEL 编号和修复词识别；边界：AMQ 编号不识别、未登记不可比、基准不符停止写入。
- 结果及用例数：67 passed、1 skipped（缺少被忽略的模型文件），证据 `data_model/preparation/reports/camel_source_alignment_validation.md`。

### 2. 集成测试
- 本次验证数据线 CLI 到自检失败退出/报告生成，以及临时 Git 仓库的采集 → 两套 SZZ 回溯；命令同上。
- 大版本合并后的前后端集成由负责合入的一条线组织；本次不修改前后端代码，未执行全系统联调。
- 证据：`data_model/preparation/reports/camel_source_alignment_validation.md`。

### 3. 验收测试
- 对照本 change 两份 spec 的 Scenario 执行数据线测试，运行 `openspec validate camel-source-alignment --strict`。
- 结果：本 change 及两份同步仓库名和样本规模的未归档提案均 valid，11 份活规格全部通过 strict 校验。
- 版本固定核验命令：`git ls-remote https://github.com/apache/camel.git refs/tags/camel-4.23.0 'refs/tags/camel-4.23.0^{}'`。
- 证据：`data_model/preparation/reports/camel_source_alignment_validation.md`；尚未将合成输入测试等同于全量验收。

### 4. 非功能验证
- 可靠性：基准不符时不得进入回溯或写文件，测试命令与证据同上。
- 性能、安全接口、前端易用性：本 change 不触及，未重跑相应测试。

### 5. 已知缺口与后续计划
- **全量采集与训练未在本机重跑**：无 Camel 全量仓库与训练模型。归属 model 蒋励；计划节点 = #68 合入窗口内（2026-10-17 前），在具备数据环境的机器上按 `docs/model/data-pipeline.md` §5 复现全量采集 + 12 模型训练，产出替换 `data_model/preparation/reports/` 下对应报告；如设备未到位，在周报「已知缺口」中如实登记实际可用日期，不虚构复现结果。
- 上游全量数字仅作为已提交证据引用；本次结果、命令与限制记录于验证报告，不倒填验收。
- 静态检查：测试文件通过；SZZ 脚本仍有 3 条可在基线复现的 lint 告警，详见验证报告，不扩大本次修复范围。

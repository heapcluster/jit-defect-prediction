# 提示词：模型线单元测试用例生成（数据链路/训练/权重）

> 用途：记录模型线单元测试用例生成时使用的提示词与产出摘要，供审核与复现参考。
> 关联提交：`1d6b06c`。

## 基本信息

- 使用工具：CodeBuddy（DeepSeek-V4.1-Flash）
- 使用日期：2026-11（用例生成期）
- 关联测试文件：`data_model/tests/`（16 个文件，163 条）
- 关联文档：`docs/database/README.md`（数据采集与特征链路）、`docs/database/commit_feature.md`
- 来源标注：`[AI生成-人工修改]`（AI 生成骨架，人工补充核心断言）

## 提示词原文

```text
你是机器学习数据链路的测试工程师。为 JIT 缺陷预测项目的 data_model 模块编写单元测试。

业务背景：
- 固定数据源为 Apache Camel tag camel-4.23.0（commit b2329103...），EXPECTED_HEAD 会校验版本
- SZZ 判据：大小写不敏感的词首边界 \b(fix|bug|patch)，且必须同时含 CAMEL-<数字>
- 训练主标签是 szz（行级回溯）；szz_lite 是文件级对照；未打标提交的 is_bug_inducing 保持 NULL
- 正样本比例落在 40%-60% 外时脚本给出告警（ABNORMAL_LOW=0.40 / ABNORMAL_HIGH=0.60）
- 训练/检验按 committed_at 时间序前 70% / 后 30% 切分，禁止随机切分
- 特征为 Kamei 14 维，列序以 expert/models/feature_order.txt 为准

编写要求：
1. pytest，纯函数用例不依赖网络与真实全量数据；需要 Git 的用 tmp_path 建临时仓库
2. 覆盖正常、边界、异常：如 SZZ 标签 0/1/null 三态、时间序切分边界、空数据集
3. 断言业务语义：标签取值只能是 0/1/null；切分不得打乱时间序；正样本比例计算口径
4. 依赖 torch/lightgbm/xgboost/pytorch_tabnet 的用例用 pytest.importorskip，且只跳过真正依赖它的参数
5. 文件头加来源标注注释（§2.1）

约束：
- 不改 pipelines/ 下的训练脚本
- 不引用历史报告数字冒充当前实测
```

## 大模型输出摘要

- 生成 16 个文件、163 条用例：
  - SZZ 与数据源：`test_szz_labeling.py`（42，参数化）、`test_camel_source.py`（1）、`test_text_source.py`（15）
  - 切分与样本：`test_split_dataset.py`（17）、`test_extract_features_pure.py`（15）、`test_single_commit_features.py`（4）
  - Effort 评估：`test_effort_budget.py`（9）、`test_effort_scope_and_narrative.py`（5）、`test_e2e_effort_curve.py`（2）
  - 特征与消融：`test_feature_ablation.py`（11）、`test_embedding_cache.py`（6）
  - 权重与交付：`test_verify_all_weights.py`（15）、`test_model_registry_parity.py`（11）、`test_official_entry_import.py`（4）、`test_from_saved_isolation.py`（3）、`test_fused_report_coverage.py`（3）
- 模型线 163 passed

## 人工审核与修改记录

- **审核结果**：修改后采纳
- **修改内容**：
  - `test_model_registry_parity.py` 把 `importorskip("lightgbm")` 收窄到仅 `lgbm` 参数，避免 `et`/`svm` 被连坐跳过
  - `test_camel_source.py` 的回退查找 docstring 改为与代码实际行为一致（先根路径、再 preparation/）
  - 7 个文件的"三例"过时描述改为"单元测试"
  - `test_text_source.py` 删除一条无意义断言（对常量元组做成员判断）
- **核心断言复核**：SZZ 三态、时间序切分、14 维列序已与 `pipelines/` 实现比对，见 [`../README.md`](../README.md)

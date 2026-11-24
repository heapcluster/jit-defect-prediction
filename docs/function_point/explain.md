# 预测结果解释（功能 7）

实现状态：已实现　期次：一期

## 一句话概述

独立的 XAI 工具：通过解释器注册表为指定模型包与输入样本生成至少 SHAP、LIME 两种统一结构解释，不支持的组合用 `reason_code` 行明确交付而非静默缺行。

## 1 职责与不负责范围

**负责**：

- 建立 XAI 解释器注册表与“模型族 × 技术”兼容矩阵，一期至少实现并验证 SHAP 和 LIME。
- 接收模型包和特征输入，按所选技术与参数计算特征原值、贡献、方向、排名和版本信息。
- 提供统一解释文件、技术切换、缓存和可选多技术比较；耗时任务进入统一 job 生命周期。
- 对不支持的模型族、输入形态或技术返回明确原因码与说明，保证每个请求样本都有结果或原因记录。

**不负责**：

- 训练、预测、修改概率或标签、行级定位、修复建议和 CI 阻断。
- 把解释限制在 expert 线而不给兼容矩阵，或在预测服务内部隐式执行解释。
- 让具体 SHAP/LIME 实现成为 localization 的直接依赖。

## 2 独立运行入口

```bash
python -m app.cli explain techniques
python -m app.cli explain run \
  --model-package model_package.zip --input clean_dataset.csv \
  --technique shap --params shap.json --out ./out
python -m app.cli explain run \
  --model-package model_package.zip --input clean_dataset.csv \
  --technique lime --compare shap --out ./out
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `explain techniques/run` | 模型包、输入文件和技术名即可运行，与 API 共用解释器注册表 |
| 注册表 API | `GET /api/explain/techniques` | 返回技术、参数 schema、兼容矩阵和默认技术 |
| 单条 API | `POST /api/explain` | 详情编排同步解释单条提交；只读已存输入与已加载模型，不产交换文件 |
| 任务 API | `POST /api/explain/run` | multipart 上传模型包与输入文件，单样本或批量均返回可跟踪的 `job_id` |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | `kind=explain` 的五态、进度、日志、取消与重试 |
| 下载 | `GET /api/explain/outputs/{job_id}/{name}` | 下载 explanations、比较结果与 manifest |

所有 HTTP 端点（含下载）必须使用 `X-API-Key`。提交详情需要解释时，由详情编排并行调用 predict 与本模块；predict 响应不含 explanation，predict 服务不得调用本模块。

## 3 输入契约

- 模型输入遵循 [`../file-contracts.md`](../file-contracts.md) §3.3 `model_package.zip`，加载前校验 checksum、模型元信息、特征顺序和列宽。
- 待解释提交由 §3.2 `clean_dataset.csv` 或 §3.1 `collected_commits.csv` 提供；两表不含 14 维 / `is_test`，expert 的特征按模型包 `feature_order.txt` 从绑定仓库现算，semantic 用预计算向量或冻结头在线编码。模型包与提交表就是主输入。§3.4 `predictions.csv` 仅为可选版本与范围核对输入，不提供它也必须能完成解释，不要求 predict 服务在线。
- 本模块配置包括 `technique`、技术专属 `params`、`feature_version`、`top_n`、`compare_techniques[]` 和缓存策略；缺省技术读取 `user_config.default_xai`。
- 注册表结合登记算法标识与实际已加载模型识别 tree/linear/tabular/text：SHAP 支持树/线性，LIME 支持表格概率模型，文本或缺少输入形态的模型明确给原因。算法库的粗粒度 family 不冒充具体解释器适配证据；不会悄悄换技术。
- 输入缺少模型所需特征、版本不符或列宽不符时明确失败；不能通过填 0、截断或重排列猜测兼容。

## 4 输出契约

| 输出 | 文件与内容 |
|---|---|
| 统一解释 | `explain_explanations_<job_id>.csv`，可选 `.xlsx`；逐行严格遵循 §3.7 explanations schema |
| 技术比较 | `explain_comparison_<job_id>.json`：同一输入在不同技术下的结果引用、参数和状态，供并排展示 |
| 运行摘要 | `explain_summary_<job_id>.json`：样本数、成功数、不支持数、缓存命中、技术与版本统计 |
| manifest | 每个产物伴同名 `explain_<artifact>_<job_id>.manifest.json`，满足 §3.9，记录模型/输入 checksum、技术参数与代码版本 |

命名统一为 `<module>_<artifact>_<job_id>.<ext>`。不支持的组合必须按 §3.7 产 `reason_code` 行：feature 与 contribution 留空、reason_code 非空，并附可展示说明；不得静默缺行或只给空白区域。所有支持的技术共用同一结构、排序和方向语义，解释过程只读，不改变预测结果。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| `default_xai` | `user_config` 全局键 | 默认 `shap`，须属于注册表，重启恢复 |
| SHAP/LIME 参数 | run 配置 + 技术 schema | 背景集、采样数等按注册表校验并入快照 |
| `explain.cache_ttl` | `user_config` 命名空间键 | 非负时长；模型/特征/技术参数变化使缓存失效 |
| `explain.compare_enabled` | `user_config` 命名空间键 | HTTP 多技术比较默认 false，显式开启；CLI 的 --compare 是本次独立运行的明确选择 |
| 展示特征数量 | run `top_n` 或 `page_prefs` | 默认 8，只影响展示，不截断交付文件中的原因行 |

## 6 状态持久化

- 解释创建 `job.kind=explain`，使用统一五态并持久化技术、参数、输入引用、进度和错误日志；同 kind 互斥，重启遗留 running 置 failed。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore；失败或不支持均保留可诊断结果，不把部分空文件标为完整成功。
- 缓存键至少包含输入样本、模型包 checksum、特征版本、技术和参数；命中缓存不重复计算，版本变化不得读取旧解释。
- `default_xai`、`explain.cache_ttl` 和 `explain.compare_enabled` 落 `user_config` 并重启恢复；每次运行固化注册表/兼容矩阵版本、模型与特征版本。
- LIME 0.2.0.1 已锁版于唯一 environment.yml；固定 seed/num_samples/kernel_width 可重算。线性 SHAP 为 log_odds，树为 tree_raw，LIME 为 local_probability_coefficient；保留符号、rank、raw_value，数值不能跨尺度直接相加。无真实背景时明确记录零/合成参考。
- 模型包解释在跨平台受限子进程内执行，不加入在线注册表；macOS 用系统 sandbox-exec，Windows 与其它平台用不可卸载的 Python 审计钩子限制文件读写/网络/子进程/动态库，pickle 只在收紧后的子进程内反序列化，父进程永不执行未受权限衡量的权重。执行有 120 秒墙钟/90 秒 CPU（Windows 等价墙钟约束）/32MiB 输出上限，超时、无效输出和不支持都交付原因行。

## 7 与其他模块边界

- 主握手是 train 的 §3.3 模型包与 clean/collect 的 §3.1/§3.2 特征文件；predict 的 §3.4 预测文件只作可选核对。任何上游服务或既有预测文件都不是解释运行前提。
- localization 只消费 §3.7 统一解释，不直接实例化 SHAP/LIME；本模块不调用 localization。
- 详情页可以并行调用 predict 和 explain，但这是外部展示编排；predict 内部禁止触发解释，解释失败也不影响预测响应。
- 页面层作为⑤预测的子页，可从预测结果/提交详情带入 commit/model；模块本身不依赖⑤在线，仍可独立上传模型包与特征文件运行。
- `algorithm.family` 与 `user_config` 属于配置元数据；独立 CLI 可使用相同登记信息的快照完成兼容性校验。

## 8 验收标准

fixtures 为测试内联合成的 AI 生成未审核模型/特征/兼容组合，含正常、边界、非法三类；在无 predict 服务、空业务库环境下，CLI/API 均可独立生成解释文件。

- 同一提交在同一兼容模型上分别运行 SHAP 与 LIME，均有统一结构、可排序且含模型/特征版本的结果；技术切换和并排比较生效。
- 至少一个不支持的模型与技术组合产生 §3.7 `reason_code` 行，feature/contribution 留空且请求样本不缺失；predict 页面不受影响。
- checksum 错误、特征缺失、列宽不符、未知技术和参数越界均明确失败，不伪造贡献；输入文件与 manifest 校验完整。
- 默认技术、缓存和比较配置重启后保持；缓存命中不重复计算，模型或特征版本变化后旧缓存不可命中。
- 承接 TODO/07：注册表、兼容矩阵、统一结构、缓存、失败原因、主要模型族和技术切换均有测试；五态、互斥、取消、重试和重启中断通过。

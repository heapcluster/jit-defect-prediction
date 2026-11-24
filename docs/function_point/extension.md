# 多种形态拓展（功能 9）

实现状态：未实现　期次：二期

## 一句话概述

二期形态适配工具：以同一 CLI/容器分析内核组合前八项交换文件，为独立客户端、VS Studio、Eclipse、CI/CD 和提交事件提供一致报告与可配置门禁，不复制业务逻辑。

## 1 职责与不负责范围

**负责**：

- 将核心模块封装为统一分析内核 CLI 与容器入口，接收仓库/提交范围及上述模块的文件组合，编排所需工具并汇总报告。
- 提供独立桌面/IDE 客户端、VS Studio 插件、Eclipse 插件和 CI/CD 步骤的适配层，共享认证、配置、结果结构和错误语义。
- 接收 Git hook、Webhook 或流水线提交事件，完成验签、去重、重试和日志脱敏。
- 默认以建议模式输出报告；只有显式开启严格模式时才按独立门禁阈值给出 block 结论。
- 支持本地文件离线运行和远程服务运行，报告附内核与契约版本。

**不负责**：

- 重新实现采集、清洗、训练、预测、评估、解释、定位、修复建议或指标公式。
- 在前八项尚未独立验收时替代其核心实现，或默认阻断所有合并。
- 同时支持所有 IDE 版本；二期只交付明确版本范围内的可运行原型。

## 2 独立运行入口

```bash
python -m kernel analyze \
  --repo /path/to/repo --commits HEAD~5..HEAD \
  --model-package model_package.zip --input clean_dataset.csv \
  --xai shap --report json,md,html --strict-mode false --out ./out

docker run --rm -v "$PWD:/work" jit-kernel analyze \
  --repo /work/repo --commits HEAD --input /work/clean_dataset.csv \
  --model-package /work/model_package.zip --report json,md --out /work/out
```

| 形态 | 入口 | 契约 |
|---|---|---|
| CLI / 容器 | `python -m kernel analyze`、`docker run jit-kernel analyze` | 同一参数与交换文件契约，容器是 CI/CD 的统一执行入口 |
| 独立客户端 | 二期审核 Electron/Tauri 或轻量 CLI + Webview 选型 | 打开本地仓库、选择提交与文件、运行分析并查看报告 |
| VS Studio / Eclipse | `plugins/vsstudio/`、`plugins/eclipse/` | 展示风险、解释、可疑行和建议，只调用内核或服务 |
| CI/CD | 同一镜像或命令 | 报告作为流水线附件，按建议/严格模式返回门禁结论 |
| 提交事件 | `POST /api/events/commit`（二期） | HMAC 验签、事件去重、失败重试，编排预测/解释的异步 job 与定位的同步调用 |

客户端和插件可配置远程服务地址；调用所有 HTTP 端点必须携带 `X-API-Key`，事件端点还须验证 HMAC。凭证由平台安全存储保管，不写入仓库、报告或日志。

## 3 输入契约

- 内核直接复用 [`../file-contracts.md`](../file-contracts.md)：§3.1 collected_commits、§3.2 clean_dataset、§3.3 model_package 与 train_testset、§3.4 predictions（含透传真标签）、§3.6 评估结果、§3.7 explanations、§3.8 定位结果与 §3.9 manifest。旧 §3.5 labels 已废止。按用户选择的分析范围接收必要组合，不定义第二套列名。
- 仓库与提交范围用于需要采集或源码的场景；仅上传既有交换文件时可离线分析。模型包、预测、标签、解释和定位文件均可按各核心模块的独立契约直接提供。
- 通用配置包括报告格式、分析范围、XAI 技术、定位参数、远程端点和输出目录；严格模式、阻断阈值、失败策略、事件去重窗口与重试次数单独配置。
- 事件载荷必须含可唯一识别的事件 ID、仓库和提交信息以及有效 HMAC 签名；重复事件返回已有运行关联号，签名失败拒绝。
- 严格模式阈值与预测标签阈值、风险展示阈值分键；失败策略分别定义分析服务异常、模型不可用和仓库不可访问时的 warn/fail 行为。

## 4 输出契约

| 输出 | 文件与内容 |
|---|---|
| 统一报告 | `extension_report_<job_id>.json`，可选 `extension_report_<job_id>.md`、`.html`；引用核心模块原始结果，不重新定义其 schema |
| 门禁结论 | `extension_gate_<job_id>.json`：模式、阈值、pass/block/warn、命中提交和失败原因；建议模式只报告不阻断 |
| 核心产物包 | `extension_artifacts_<job_id>.zip`：按需包含 §3.4 predictions、§3.6 评估、§3.7 explanations、§3.8 定位/建议/patch preview 及各自 manifest |
| 事件回执 | `extension_event_<job_id>.json`：事件 ID、验签/去重结果、触发的既有 kind 与运行关联号，不包含签名或令牌 |
| manifest | 每个拓展产物伴同名 `extension_<artifact>_<job_id>.manifest.json`，满足 §3.9，附内核版本、核心文件 checksum 和配置快照 |

命名统一为 `<module>_<artifact>_<job_id>.<ext>`；`job_id` 是内核运行关联号，具体异步工作仍只使用六类 kind。报告中的风险、解释、定位、建议和指标必须来自对应核心文件；CI 附件、插件和 Web 展示同一结构。patch 永远只是预览，拓展形态不得应用它。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| 核心全局键 | `user_config` | `decision_threshold`、`default_xai` 等沿用核心单源；模型由每次分析显式选择 |
| 核心命名空间键 | `user_config` | collect/clean/train/predict/explain/localization 键由原模块拥有，内核只读 |
| `extension.report_formats` | `user_config` 命名空间键（二期） | 默认 `json`，可选 md/html |
| `extension.strict_mode` / `extension.gate_threshold` | `user_config` 命名空间键（二期） | 默认 false / 独立阈值；开启严格模式才可阻断 |
| `extension.failure_policy` | `user_config` 命名空间键（二期） | 默认 warn，可按失败类型配置 fail |
| `extension.event_dedup_window` / `extension.retry_max` | `user_config` 命名空间键（二期） | 正时长 / 非负整数，重启恢复 |
| 端点与凭证 | 客户端安全存储或 CI secret | 远程地址可配；`X-API-Key`、HMAC secret 不入库、不进报告 |

## 6 状态持久化

- 内核运行关联号、事件回执、配置版本和输出 manifest 持久化；触发的异步工作沿用 `collect / clean / train / predict_batch / evaluate / explain` 六类五态，不新增 extension/localize kind。
- **提交事件编排**：事件验签去重后，内核按配置顺序编排——① `POST /api/predict`（单条同步，显式传 `model_name`）拿到风险；② 需要解释时并行 `POST /api/explain`（显式模型）或提交 `kind=explain` 任务；③ 需要定位时显式调用 `POST /api/localize/run`，提交 `predictions.csv`、可读仓库与 40 位 `commit_hash`，可选解释文件。定位是同步端点且不属于六类 job，内核把它的产物引用记入同一运行关联号，不创建 localize kind，也不把同步调用伪装成 job。
- 同 kind 互斥、重启 running 置 failed 等规则由核心任务服务执行；事件重试复用原运行关联号，重复投递不重复分析。已异步完成的子步骤不因重试重复执行，同步定位按相同输入重跑并覆盖同一关联号下的文件。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore；插件、客户端与 CI 可通过同一输出引用获得报告和核心文件。
- 事件去重记录至少包含事件 ID、提交哈希、载荷摘要和运行关联号，可使用持久化事件日志；不得把签名原文或凭证写入 `job.params_json`、日志和报告。
- 严格模式、阻断阈值、失败策略和二期命名空间键持久化并重启恢复；关闭严格模式立即回到建议模式，历史报告保留当时门禁快照。
- 报告记录内核/契约/代码版本与各核心输入 checksum，保证不同载体可复核同一次分析。

## 7 与其他模块边界

- 前八项完成独立验收后才启动二期交付；内核只编排它们的 CLI/服务和交换文件，各载体不持有业务算法。
- 对核心模块的依赖是所需文件 schema 与公开能力契约，而不是某个 Web 页面、数据库记录或另一载体在线。
- storage 继续负责可选展示导入、配置和任务状态；extension 不建立第二套配置中心或结果库。
- 默认建议模式不阻断；严格模式只读取独立门禁配置并返回结论，合并平台的实际阻断由 CI 适配层执行。

## 8 验收标准

fixtures 位于 `tests/fixtures/files/extension/`，含正常、边界、非法三类交换文件组合、事件载荷和门禁配置；核心模块可替换为符合契约的测试执行器以验证适配层。

- CLI 与容器对同一文件组合生成结构一致的 JSON/Markdown/HTML 报告和 manifest；独立客户端能打开本地仓库并完成一次分析。
- VS Studio 与 Eclipse 原型均能展示风险、解释、可疑行和四段式建议，且不包含核心算法实现；各自有安装与版本说明。
- CI 示例在提交后生成报告附件；默认建议模式不阻断，严格模式按阈值阻断，关闭后立即恢复建议行为，warn/fail 策略符合配置。
- 事件验签失败拒绝，重复事件只分析一次，失败可重试；日志、事件回执和报告的敏感信息扫描为零。
- 各形态不破坏现有 Web；核心文件逐列校验仍符合 §3.1–3.9，patch preview 不被应用，输出目录与配置在重启后可恢复。
- 承接 TODO/09：每种形态至少一个可运行示例和截图/录屏，CLI 契约、插件接口、CI 报告、事件去重/重试/脱敏及取消门禁说明齐全。

# 数据清洗与预处理（功能 3）

实现状态：已实现　期次：一期

## 一句话概述

独立的清洗工具：上传 `commits.csv` 并编排九操作处理链，以 preview/apply 两种模式产出逐步统计、特征前后分布图和可选的 `cleaned.csv`，无需采集模块或库中数据先行存在。

## 1 职责与不负责范围

**负责**：

- 提供九操作注册表，声明每个操作的输入、输出、参数 schema、默认值和顺序约束；处理链支持选择、排序、启停与调参。
- preview 只产统计、排除样本和图表，不写业务库、不产新数据集；apply 额外产 `cleaned.csv`，供独立下载或可选导入。
- 记录每步前后行数、删除/修改数、标签分布、耗时、排除原因，以及指定特征的分布统计与图像。
- 保存完整处理链、种子、输入输出 checksum、特征顺序和特征版本，保证同输入同配置可复现。

**不负责**：

- Git 采集、SZZ 判据的第二份实现、模型训练、预测、评估阈值或模型阈值管理。
- 新增或重定义 Kamei 特征集合；标准化不得造成测试集信息泄漏。
- 把页面作为唯一执行入口，或要求用户先导入数据集才能运行。

## 2 独立运行入口

```bash
# 从 data_model 目录运行；仓库根可直接运行 data_model/preparation/clean.py
python -m preparation.clean run \
  --input commits.csv --chain chain.json --mode preview \
  --features ns,nd --seed 42 --out ./out
python -m preparation.clean run \
  --input commits.csv --chain chain.json --mode apply --format csv --out ./out
python -m preparation.clean operations
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `python -m preparation.clean run/operations` | 文件与处理链即可运行，与 API 共用注册表和变换实现 |
| 注册表 API | `GET /api/clean/operations` | 返回九操作元数据、参数 schema 和顺序约束 |
| 任务 API | `POST /api/clean/run` | multipart 上传 CSV/XLSX + `mode=preview\|apply` + chain，返回 `job_id`；可选 `dataset_id` 仅作便利输入 |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 状态、逐步进度、日志、重试与取消 |
| 下载 | `GET /api/clean/outputs/{job_id}/{name}` | 下载 cleaned、统计、图与 manifest |
| 展示导入 | `POST /api/storage/import` | 仅 apply 产物可选导入；preview 无此动作 |

所有 HTTP 端点（含图像与文件下载）必须使用 `X-API-Key`；图像由鉴权 fetch 转 ObjectURL 展示。

## 3 输入契约

- 主输入为 [`../file-contracts.md`](../file-contracts.md) §3.1 `commits.csv` 的 CSV/XLSX 形式；列名、顺序、空标签和编码以该节为唯一权威。可选 `dataset_id` 只让 run 端点读取已导入的同类文件，不上传文件仍可完整运行。
- 本模块配置包含 `steps[]`、`features[]`、`seed`、`mode` 和 `format`。每个 step 包含注册表操作标识、启停状态与参数；未知操作、参数越界、顺序冲突或随机切分请求在创建任务前拒绝。

| 操作 | 职责与默认约束 |
|---|---|
| `merge_filter` | 链首；只凭 parent_hash 多个有效父哈希过滤合并，不凭 message 猜测；apply 不允许多父记录残留 |
| `szz_label` | 文件已有 SZZ 方法证据复核/复用，方法不一致拒绝；不调用 Git、不重新推断标签，缺方法保留真标签并警告 |
| `d5_exclude` | 原 02 脚本判据单源，在 szz_label 后排除同方法的 NULL 修复候选，记录文件缺回溯证据，不冒称新 SZZ 实测 |
| `anomaly_exclude` | max_abs 默认 1e6，排除真实特征异常；正样本比例落在原 40%–60% 自检区间警告，不按比例删标签 |
| `label_validate` | 同表提交哈希、标签、特征严格对齐；重复 hash 拒绝，NULL 不填 0 |
| `feature_align` | 固定 Kamei 14 项列序与版本，先于 log/standardize |
| `log_transform` | 输入本就是 v1 对数值，报告跳过，不能二次 log 或做有损逆变换 |
| `standardize` | 仅最终过滤后的时间序训练侧拟合 13 项非 fix 特征，与图特征选择无关；manifest 记录 scaler 与训练哈希，输出 v1-standardized 独立版本 |
| `time_split` | 链末，默认时间序 70/30，复用原 05 的 floor 和严格时间断言；同秒跨边界拒绝，0/1 行明确报告空侧 |

- `features[]` 指定需要输出前后统计和分布图的特征，缺省为 Kamei 14 项；显式空数组或未知特征前置拒绝，不能关闭全部分布图。preview/apply 均至少交付一组前后分布图；`seed` 不得开启随机时间切分。
- 上传校验覆盖大小、扩展名与魔数、schema、类型和 CSV 公式注入；非法输入不进入处理链。

## 4 输出契约

| 输出 | 文件与模式 |
|---|---|
| 清洗数据 | `clean_cleaned_<job_id>.csv` 与 `.xlsx`；仅 apply 产出，format 决定优先格式，schema 严格遵循 §3.2 |
| 每步统计 | `clean_steps_stats_<job_id>.json`；两种模式均产，逐步包含 `rows_before/after/removed/label_dist/elapsed_ms/excluded_samples`，并记录 modified、前后标签分布和排除原因 |
| 特征统计 | `clean_feature_stats_<job_id>.json`：所选特征的均值、中位数、标准差、分位数、缺失数及图表数据 |
| 分布图 | `clean_feature_distribution_<feature>_<job_id>.png`；两种模式均必须交付，至少一组并覆盖所选特征的前后直方图或箱线图；无样本侧明确标注空数据，不伪造数值 |
| manifest | 每个产物伴同名 `clean_<artifact>_<job_id>.manifest.json`，满足 §3.9；处理链、种子、特征顺序/版本与输入输出 checksum 全量入快照 |

所有文件遵循 `<module>_<artifact>_<job_id>.<ext>`。preview 不生成 `clean_cleaned_*`，apply 不覆盖上传原文件；可选导入 apply 产物时登记为新数据集版本，原始版本保留。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| `clean.chain_templates` | `user_config` 命名空间键 | 保存可复用处理链模板，含步骤、顺序和参数版本，重启恢复 |
| 步骤选择、排序、启停和参数 | 本次 run 配置 | 注册表 schema 与顺序约束校验 |
| `features[]` / `seed` / `mode` | 本次 run 配置 | 缺省 Kamei 14 项、显式选择至少 1 项 / 42 / preview 或 apply |
| 时间切分比例 | `time_split` 参数 | 默认 70/30；只改比例，不允许随机或取消时间边界断言 |
| `default_dataset` | `user_config` 全局键 | 仅用于下拉默认选项 |
| 输出格式 | 本次 run 配置 | CSV 默认，XLSX 可选 |

Kamei 14 维列序、log（`fix` 除外）、SZZ 判据单源和 NULL 标签语义是不可破坏的不变量；可配置不等于可另造口径。

## 6 状态持久化

- 两种模式均创建 `job.kind=clean`，使用统一五态；job 保存模式、处理链、进度、错误日志、输入输出引用和重试次数。同 kind 互斥，重启遗留 running 置 failed。
- preview 的“不写库”指不写 commit、feature、dataset 等业务表；任务状态、配置快照和文件输出引用仍需持久化。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore；失败时不保留可被误认为成功的半成品，重试使用同一配置快照。
- `clean.chain_templates` 落 `user_config`，重启恢复；每次执行的处理链和版本随 job、manifest 固化，模板后续变化不影响历史结果。
- apply 文件及统计可独立下载；显式导入 storage 后才生成展示用数据集版本，原始数据不覆盖。

## 7 与其他模块边界

- 与 collect 的依赖仅为 §3.1 文件 schema 兼容；任意满足该 schema 的文件都可清洗，Camel、其他仓库或测试 fixture 均可。
- train 接收 §3.2 文件即可运行；本模块不读取训练服务状态。SZZ 判据来自 collect 单源，但不调用 collect 在线服务。
- storage 仅提供可选导入与配置/任务持久化，不是处理链的数据来源前提。
- 本模块不计算模型指标；训练摘要与模型性能统一复用 evaluate 的指标单源。

## 8 验收标准

验收夹具为测试内联合成的 AI 生成未审核数据，含正常、边界、非法三类；在空库且未运行 collect 的情况下，CLI 与 API 分别用上传文件完成 preview 和 apply。

- 九操作均可查询、启停、排序和调参；非法操作、参数、顺序与随机切分被前置拒绝，注册表和变换逻辑有单元测试。
- preview 不写业务表且不产 cleaned；apply 产 §3.2 文件且原输入不变。两种模式均产逐步统计、排除原因与至少一组前后分布图；省略 features 仍生成默认图，显式空数组前置拒绝。
- 同输入同链同种子重跑主表、PNG 与统计数值一致；真实 elapsed_ms、执行时间和 job_id 不作为跨运行字节一致项。manifest、固定 14 项特征顺序/版本和 checksum 完整，CLI/API 结果等价。
- 14 维列序与 log、SZZ 复用、时间序禁随机、NULL 标签不被破坏；缺列、错类型、公式注入、超大文件和空标签场景有明确结果且不伪造分布。
- 承接 TODO/03：可预览步骤前后样本数、标签分布、特征分布；apply 可选导入为新版本且保留原版本；操作注册表、统计、版本生成、图表接口和重启恢复均有自动化测试。

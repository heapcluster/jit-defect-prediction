# 功能点 1 数据库存储与配置中心

一句话：把各模块产物按 schema 内部自动登记进关系库，按数据链路汇总历史产物并支持整链删除，同时提供配置中心管理阈值与页面偏好；页面不提供文件导入。

实现状态：已实现　期次：一期

表结构见 [`../database/`](../database/)；API 见 [`../api/storage.md`](../api/storage.md)、[`../api/datasets.md`](../api/datasets.md)、[`../api/config.md`](../api/config.md)。设计图功能 ① 以后台服务、`/storage` 产物中心与 `/settings` 的配置界面体现；存储页只有「产物库」与「数据链路」两个子签，负责查看、选择、下载与删除，不提供文件导入；按表导出接口仅保留供数据集 CSV 导出使用，界面不提供按表导出入口。链路关系由 `job.chain_id` / `parent_job_ids` 显式记录，整链删除已实现。

## 1 职责

- 内部自动登记：清洗成功后按 schema 识别提交表、清洗表、预测表、模型文件与图，按主键幂等 upsert；页面不暴露上传入口。
- 维护数据集登记与统计回填，支持从批次产物登记数据集。
- 按 `job.chain_id` / `parent_job_ids` 汇总数据链路，提供链路表与整链删除。
- 按表白名单导出 CSV/XLSX：按请求格式只生成一份核心文件，manifest 作为内部校验记录随批次生成。
- 配置中心：读取、批量写入、单键写入、删除与回落。

## 2 不负责

- 不执行 SZZ、清洗、训练、预测、评估、解释、定位。
- 不修改模块产物，不把内部登记当作模块运行前置；页面不接受用户上传。
- 不维护模型权重训练过程，只登记模型文件与图。

## 3 输入

以下文件由模块产物在内部自动登记时进入，页面不提供上传。

| 类型 | 说明 |
|---|---|
| 提交/清洗表 | CSV/XLSX，列匹配 `collected_commits` 或 `clean_dataset` |
| 预测表 | 列严格等于 `predictions`，版本须与库中模型一致 |
| 模型文件 | `.pkl` + 侧车 meta，或外部交付 ZIP（`model_meta.json`、`feature_order.txt`、`checksum.sha256`、`.pkl`） |
| 图 | PNG + 同名 manifest，`figure_type` 在契约内 |
| 配置 | `config` 键值，按 schema 校验 |

## 4 流程

内部自动登记（页面不参与）：

1. 校验文件名、编码、列、行数、公式注入与 manifest/checksum。
2. 识别 schema；歧义或未知 schema 直接拒绝该文件。
3. 单文件事务 upsert，记录 `inserted/updated/unchanged/rejected`。
4. 刷新数据集统计（样本数、正负样本、时间范围）。
5. 导出时按表 + 过滤条件生成文件与 manifest。
6. 产物库按链路汇总任务树；删除时校验链内资产是否被链路外引用，通过后整体删除任务、产物、模型与数据集。

## 5 输出

- 内部登记：逐文件计数与错误列表；整体全部失败才返回 40001。
- 导出：`{module}_{artifact}_{job_id}.{csv|xlsx}` 单份核心文件 + 内部 manifest。
- 数据集：`dataset` + `dataset_commit` 行，状态 `ready`。
- 链路：`{chain_id, nodes[], artifacts[]}`；删除返回任务 / 产物 / 模型 / 数据集计数。
- 配置：`user_config` 行，返回 `source` 与 `value_type`。

## 6 约束

- `dataset_id` 与 `create_dataset` 互斥；同 meta 幂等（uuid5）；`create_dataset` 仅创建 `git_repo` 数据集，公开数据集只能由 collect 任务创建。
- 已加载模型的同名包 checksum 不同时拒绝登记。
- 导出上限 100000 行，`job`/`user_config` 的 JSON 列做脱敏。
- 配置引用对象（模型、数据集）必须已登记。
- 整链删除必须带 `confirm=true`；链内资产被链路外任务引用时拒绝（40001）并列出引用方。

## 7 验收

- 内部自动登记可识别四类文件，非法列/manifest/checksum 被拒。
- 重复登记幂等，统计正确。
- 导出列与库表一致，过滤与上限生效。
- 依次跑收集 → 清洗 → 训练 → 预测 → 评估后，链路接口返回同一条链；训练多模型时分叉不拆链。
- 整链删除缺 `confirm=true` 被拒；有外部引用时被拒并列出引用方；无外部引用时任务、产物、模型与数据集一并清除。
- 配置读写、删除回落与跨键校验正确。
- 数据库为空不影响任何模块独立运行。

## 8 边界

storage 是展示与持久化的可选层。模块间交接只依赖文件与 manifest；数据库缺失、内部登记失败或被清空，都不改变模块产物与独立验收结论。



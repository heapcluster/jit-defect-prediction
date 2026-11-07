# szz-labeling Specification

## Purpose
在提交粒度上判定一次提交是否引入缺陷：先识别修缺陷提交，再回溯到引入缺陷的那次提交，产出带方法标记、可对照、可复现的缺陷标签。

## Requirements

### Requirement: 识别修缺陷提交

系统 MUST 按可复核的判据识别修缺陷提交，且判据 MUST 记录在 `docs/common/data-pipeline.md`，MUST NOT 只存在于实现代码里。

#### Scenario: 修复提交被识别

- **WHEN** 一条提交记录同时命中缺陷编号与修复语义两类判据
- **THEN** 该提交被标记为修缺陷提交并进入回溯环节

#### Scenario: 修复语义的匹配口径

- **WHEN** 判定一条提交的 message 是否含修复语义
- **THEN** 用**词首边界**匹配（`\b(fix|bug|patch)`，大小写不敏感）；不使用无边界子串匹配。假阳性数量须在固定 Camel 版本上实测后记录，不引用已删除的旧报告。

#### Scenario: 判据可复算

- **WHEN** 他人按 `docs/common/data-pipeline.md` 固定的版本与当前脚本判据复算
- **THEN** 命中统计与本次生成的报告逐项一致；报告缺失时如实记为未验证，MUST NOT 借用历史数字

#### Scenario: 判据全部落空

- **WHEN** 一条提交记录不含任何可识别的缺陷编号
- **THEN** 该提交被判定为「非修复提交」，不进入回溯环节，但 MUST 保留在中间产物中供人工复核

### Requirement: 回溯引入缺陷的提交

系统 MUST 把修缺陷提交回溯到引入缺陷的那次提交；离线中间结果可保留修复提交哈希以便审计，现行数据库只将 SZZ 真标签写入 `commit_feature.is_bug_inducing`。

#### Scenario: 回溯命中

- **WHEN** 被修复的代码行可定位到一次引入它的提交
- **THEN** 引入提交标为 `is_bug_inducing = 1`；修复哈希只在离线审计产物中保留，不写入现行五表

#### Scenario: 回溯无法命中（边界）

- **WHEN** 引入提交不在固定版本的历史范围内，或该次改动为纯删除而无引入方
- **THEN** 该修复提交不产生任何标签，流程 MUST 继续执行，并把「未产生标签的修复提交数」计入统计

### Requirement: 标签字段与方法标记

离线打标产物 SHALL 标明 `szz` / `szz_lite` 方法以便对照；进入现行数据库的主标签 MUST 取 `szz` 并写入 `docs/database/commit_feature.md` 定义的 `is_bug_inducing`，未打标保持 `NULL`。数据库已无 `commit_label` 表、`label_method` 和 `bug_fix_hash` 列。

#### Scenario: 两套方法并存

- **WHEN** 用两套算法对同一固定版本各打一次标
- **THEN** 两份标签可按 `label_method` 区分，互不覆盖、互不混淆

#### Scenario: 出现契约未定义的方法名

- **WHEN** 标签中出现契约未定义的 `label_method` 取值
- **THEN** 校验判定失败，必须先改契约再重跑，MUST NOT 直接进入下游

### Requirement: 正样本比例异常时先自查

打标结果 MUST 报出正样本比例。**判据 MUST 与实现同源** —— 当前 `02_szz_labeling.py` 的 `ABNORMAL_LOW` / `ABNORMAL_HIGH` 为 0.40 / 0.60，说明见 `docs/common/data-pipeline.md` 第 3 节。

#### Scenario: 比例落在异常区间

- **WHEN** 正样本比例落在判据数值区间内（当前 40%–60%）
- **THEN** 流程给出显式告警并提示先排查打标逻辑，MUST NOT 直接产出下游样本集

#### Scenario: 比例落在判据区间之外

- **WHEN** 正样本比例不落在判据数值区间内
- **THEN** 流程正常结束并输出统计表，且表中同时记录**实测比例**与**判据数值**（含判据所在文件与常量名），供他人复算

#### Scenario: 用经验描述充当判据

- **WHEN** 有人以「JIT 数据集的正样本比例是个位数到十几百分点」这类**经验描述**作为判据
- **THEN** 该说法 MUST NOT 被采纳；判据使用当前脚本中的数值，实际比例使用固定版本本次生成的报告，未重跑时不得引用旧 ActiveMQ 或旧 Camel 报告作为当前验收证据

### Requirement: 打标结果可复现

同一条流水线在同一个固定版本上重复执行 MUST 产出逐条一致的标签；两套算法的差异 MUST 可量化。

#### Scenario: 连续两次执行一致

- **WHEN** 在同一个固定版本上连续执行两次打标
- **THEN** 两份标签按 `commit_hash` 排序后逐行一致

#### Scenario: 两套方法结果不一致

- **WHEN** 两套算法对同一提交给出不同标签
- **THEN** 该差异 MUST 计入对照统计并可在报告中出示，MUST NOT 静默取其一覆盖另一

### Requirement: Camel 判据自检与报告一致

实现与报告 MUST 使用 `CAMEL-\d+` 且词首边界修复语义的同一判据。完整版本提交数登记为 84461，含编号、编号且修复语义、编号且 fix 词形的外沿分别为 38716、7787、6631。基准来源 MUST 标明为已提交的 Camel 全量报告，不得把旧 ActiveMQ 数据或合成测试当作 Camel 实测。

#### Scenario: 完整输入通过自检
- **WHEN** 基准已登记，输入条数等于完整版本总数且三项外沿全部匹配
- **THEN** 自检通过，报告和 CLI 使用同一结论

#### Scenario: 完整输入自检不一致
- **WHEN** 条数等于完整版本总数，但至少一项外沿与登记值不一致
- **THEN** CLI 非零退出，在回溯、写标签和覆盖报告之前停止

#### Scenario: 基准尚未登记
- **WHEN** 完整提交数或任一外沿尚未登记
- **THEN** 报告明确标记尚未登记且不可比，不打印 None，不误称子集或自检通过

#### Scenario: 非完整规模输入
- **WHEN** 输入条数小于或大于完整版本登记数
- **THEN** 报告说明输入规模不同、外沿不可比，不误报完整自检通过

#### Scenario: 排除旧仓库编号
- **WHEN** 消息仅包含 AMQ 编号和修复词，而没有 CAMEL 编号
- **THEN** 不进入 Camel 修复候选，报告仅描述 CAMEL 判据

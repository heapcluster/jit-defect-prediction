## Purpose

在提交粒度上判定一次提交是否引入缺陷：先识别修缺陷提交，再回溯到引入缺陷的那次提交，产出带方法标记、可对照、可复现的缺陷标签。

## ADDED Requirements

### Requirement: 识别修缺陷提交

系统 MUST 按可复核的判据识别修缺陷提交，且判据 MUST 作为文字写进 `docs/data-pipeline.md`，MUST NOT 只存在于实现代码里。

#### Scenario: 修复提交被识别

- **WHEN** 一条提交记录同时命中缺陷编号与修复语义两类判据
- **THEN** 该提交被标记为修缺陷提交并进入回溯环节

#### Scenario: 判据全部落空

- **WHEN** 一条提交记录不含任何可识别的缺陷编号
- **THEN** 该提交被判定为「非修复提交」，不进入回溯环节，但 MUST 保留在中间产物中供人工复核

### Requirement: 回溯引入缺陷的提交

系统 MUST 把修缺陷提交回溯到引入缺陷的那次提交，并在标签中记录该次修复提交的哈希。

#### Scenario: 回溯命中

- **WHEN** 被修复的代码行可定位到一次引入它的提交
- **THEN** 标签记在该引入提交上，`is_bug_inducing = 1`，`bug_fix_hash` 为该修复提交的哈希

#### Scenario: 回溯无法命中（边界）

- **WHEN** 引入提交不在固定版本的历史范围内，或该次改动为纯删除而无引入方
- **THEN** 该修复提交不产生任何标签，流程 MUST 继续执行，并把「未产生标签的修复提交数」计入统计

### Requirement: 标签字段与方法标记

标签 MUST 满足 `docs/contracts/data-fields.md` 表二 `commit_label` 的字段定义；MUST 记录 `label_method`，取值只在契约定义的方法集合内。

#### Scenario: 两套方法并存

- **WHEN** 用两套算法对同一固定版本各打一次标
- **THEN** 两份标签可按 `label_method` 区分，互不覆盖、互不混淆

#### Scenario: 出现契约未定义的方法名

- **WHEN** 标签中出现契约未定义的 `label_method` 取值
- **THEN** 校验判定失败，必须先改契约再重跑，MUST NOT 直接进入下游

### Requirement: 正样本比例异常时先自查

打标结果 MUST 报出正样本比例。当该比例落入与已有 JIT 研究明显不符的区间时，MUST 先复核打标逻辑再进入下游。

#### Scenario: 比例落在异常区间

- **WHEN** 正样本比例落在 40%–60% 区间
- **THEN** 流程给出显式告警并提示先排查打标逻辑，MUST NOT 直接产出下游样本集

#### Scenario: 比例落在合理区间

- **WHEN** 正样本比例落在个位数到十几百分点的区间
- **THEN** 流程正常结束并输出统计表

### Requirement: 打标结果可复现

同一条流水线在同一个固定版本上重复执行 MUST 产出逐条一致的标签；两套算法的差异 MUST 可量化。

#### Scenario: 连续两次执行一致

- **WHEN** 在同一个固定版本上连续执行两次打标
- **THEN** 两份标签按 `commit_hash` 排序后逐行一致

#### Scenario: 两套方法结果不一致

- **WHEN** 两套算法对同一提交给出不同标签
- **THEN** 该差异 MUST 计入对照统计并可在报告中出示，MUST NOT 静默取其一覆盖另一

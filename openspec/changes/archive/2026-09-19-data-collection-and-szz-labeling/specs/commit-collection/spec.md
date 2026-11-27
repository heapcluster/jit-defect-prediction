## Purpose

把代码仓库副本固定在登记在册的版本上，抽取符合契约字段的提交清单并过滤合并提交，为打标与特征计算提供唯一的数据基准。

## ADDED Requirements

### Requirement: 仓库版本固定

系统 MUST 把仓库副本固定在登记在册的 tag 或 commit 上，MUST NOT 以浮动的分支引用作为数据基准。固定的完整 commit 哈希、固定日期与固定方式 MUST 写入 `docs/data-pipeline.md` 第 2 节的登记表。

#### Scenario: 首次固定版本

- **WHEN** 采集流程在干净环境下首次执行
- **THEN** 仓库副本检出到登记表登记的版本，且 `HEAD` 的完整哈希与登记表逐字符一致

#### Scenario: 登记表版本缺失

- **WHEN** 采集流程执行时登记表中没有可用的版本号
- **THEN** 流程以失败退出并提示先完成版本登记，MUST NOT 回退到默认分支继续执行

### Requirement: 提交清单字段与契约一致

抽取出的提交清单 MUST 满足 `docs/contracts/data-fields.md` 表一 `commit` 的字段定义：列名逐字一致、一律 `snake_case`、时间字段统一 UTC 且以 `_at` 结尾；`commit_hash` 为唯一键，`committed_at` 建普通索引。

#### Scenario: 列名逐字对齐

- **WHEN** 比对采集产物列名与契约表一
- **THEN** 列名集合与契约完全一致，无缺列、无自造列、无改名

#### Scenario: 提交时间带非 UTC 偏移

- **WHEN** 抽取到一条提交时间带非 UTC 时区偏移的提交记录
- **THEN** 落库的 `committed_at` 为换算后的 UTC 时间，且 `committed_at` 可用于时间序排序

### Requirement: 过滤合并提交

采集 MUST 过滤合并提交，只保留实际改动代码的提交。

#### Scenario: 合并提交被排除

- **WHEN** 遍历到一条父提交多于一个的合并提交
- **THEN** 该提交不进入提交清单

#### Scenario: 仓库首个提交处理

- **WHEN** 遍历到没有父提交的仓库首个提交
- **THEN** 该提交正常进入清单，`parent_hash` 留空，流程 MUST NOT 因此中断

### Requirement: 报出采集统计

采集 MUST 输出可核对的最小统计：抽取到的提交总数与提交时间跨度（最早至最晚）。

#### Scenario: 正常输出采集统计

- **WHEN** 采集流程正常结束
- **THEN** 提交总数与时间跨度同时出现在标准输出与 `data_model/reports/` 下

#### Scenario: 采集结果为空

- **WHEN** 采集结果为 0 条提交
- **THEN** 流程以失败退出并给出提示，MUST NOT 继续进入打标步骤

### Requirement: 数据集不入库

仓库副本、中间产物与样本集 MUST NOT 进入版本库。MUST NOT 通过修改忽略规则、新增排除例外或强制添加的方式绕过这一限制。

#### Scenario: 提交前自检

- **WHEN** 采集产物生成后执行 `git status --short`
- **THEN** 输出中不出现仓库副本、样本集或模型文件

#### Scenario: 误加数据集

- **WHEN** 提交前发现采集产物已被暂存
- **THEN** 该次提交 MUST NOT 执行，先撤销暂存再提交代码与文档

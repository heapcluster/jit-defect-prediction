## ADDED Requirements

### Requirement: 历史修复参考检索

提交详情 SHALL 从同仓库 `commit_feature.fix=1` 的真实历史修复提交中返回至多 Top-K 条参考，按 `committed_at` 倒序排列。参考只含提交哈希、提交信息与时间；MUST NOT 宣称已计算语义相关度、修复方案或缺陷类型。

#### Scenario: 检索有命中

- **WHEN** 查询某提交详情且同仓库存在其他 `fix=1` 的提交
- **THEN** `fix_references.items` 返回至多 Top-K 条，按提交时间倒序，排除目标提交本身

### Requirement: 检索无命中与边界

检索无命中时 SHALL 返回空数组，页面 SHALL 展示明确空态，MUST NOT 虚构建议或阻塞页面渲染。

#### Scenario: 无命中

- **WHEN** 同仓库无 `fix=1` 的其他历史提交
- **THEN** 返回空数组，页面展示「暂无可参考的修复模式」，风险信息照常展示

#### Scenario: 低风险提交

- **WHEN** 查询低风险提交详情
- **THEN** 仍只返回同仓库真实历史修复提交；风险等级不改变参考来源

### Requirement: 检索产物不入库

检索 SHALL 只读 `commit` 与 `commit_feature`；仅将必要的说明性结果随响应返回，MUST NOT 重算标签或创建新的模型与预测行。

#### Scenario: 重复检索

- **WHEN** 对同一提交连续检索两次
- **THEN** 数据库中不新增任何行，两次响应内容一致

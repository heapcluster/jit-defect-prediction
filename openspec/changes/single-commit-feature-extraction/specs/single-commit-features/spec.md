## ADDED Requirements

### Requirement: 单条提交复用 v1 特征口径

模型线 MUST 为本地 Git 仓库 HEAD 可达的非合并提交提供按 `docs/model/feature-columns.md` 计算 14 项 v1 特征的可调用入口。输出 MUST 含有序特征向量，且与批量抽取同一提交的值逐项一致。

#### Scenario: 新提交未出现在批量 CSV

- **WHEN** 调用方提供本地仓库路径和 HEAD 可达的非合并提交哈希，且没有预生成 `commits.csv`
- **THEN** 入口从 Git 历史算出 14 项特征与提交元信息，并按冻结列序返回向量，不写批量产物

#### Scenario: 提交非法或不可达

- **WHEN** 哈希不是 40 位十六进制，或提交不在当前 HEAD 可达的非合并历史中
- **THEN** 入口明确失败，不返回伪造的全零向量，也不写批量产物

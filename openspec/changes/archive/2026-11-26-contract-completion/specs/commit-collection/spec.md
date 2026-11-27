## ADDED Requirements

### Requirement: 分支枚举

系统 SHALL 提供 `GET /api/collect/branches?repo_source=`，从远端 `git ls-remote --symref --heads` 或本地仓库 refs 枚举分支，返回 `{repo_name, branches, default_branch}`。分支列表为空时返回 40001，不允许返回空数组冒充成功。页面 MUST 通过该端点选择分支，不提供手填分支。

#### Scenario: 列分支

- **WHEN** 用户输入合法仓库路径或 URL 并刷新分支
- **THEN** 返回非空分支列表，页面默认选中 `default_branch`（不在列表时选第一项）

#### Scenario: 无可用分支

- **WHEN** 仓库没有可读分支或权限不足
- **THEN** 返回 40001 与“未找到可用分支”提示，页面保持分支下拉禁用

### Requirement: 公开数据集 URL 拉取

系统 SHALL 提供 `POST /api/collect/source-columns` 与 `source_type=public_dataset` 的 `POST /api/collect/run`。公开模式 MUST 只接受 `https`、无凭证/query/hash 的 URL；MUST 通过 `field_mapping`（目标列→来源列）与 `label_mapping`（正/负样本值）归一化为 `collected_commits`；输出 MUST 与 Git 模式同一列契约，不跑 SZZ，`label_source=public_dataset`。

收集任务 MUST NOT 预生成 XLSX；用户可见核心产物只有 `collected_commits_<job_id>.csv`。

#### Scenario: 读取字段

- **WHEN** 用户提交公开数据集 URL
- **THEN** 返回远端 CSV/XLSX 的列名，供页面做字段映射

#### Scenario: 标签映射

- **WHEN** 源标签值命中 `label_mapping.positive/negative`
- **THEN** 分别写成 1/0；空值保持未标注；无法映射的值返回 40001

#### Scenario: 与 Git 模式同契约

- **WHEN** 公开数据集任务成功
- **THEN** 产物列等于 `COLLECTED_COMMITS_COLUMNS`，可由 storage 导入或 collect resave 登记为 `public_dataset` 数据集

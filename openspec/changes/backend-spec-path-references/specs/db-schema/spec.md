## MODIFIED Requirements

### Requirement: 建表字段逐字对齐契约

系统 SHALL 按 `docs/design/data-fields.md`（契约一 v1.4，表一/二/三与 ER 图）与 `docs/model/feature-columns.md`（契约二）§2/§3 建立 `commit`、`commit_label`、`commit_feature`、`prediction` 四张表：列名逐字一致、一律 snake_case、时间字段统一 UTC 且以 `_at` 结尾；`commit_hash` SHALL 建唯一索引，`committed_at` SHALL 建普通索引；四张表 SHALL 由同一份迁移脚本建立。

#### Scenario: 列名逐字对齐

- **WHEN** 将建库产物的列名与类型同契约一表一/二/三、契约二 §2/§3 逐字段比对
- **THEN** 无缺列、无改名列、无自造列

#### Scenario: 重复提交被唯一索引拒绝

- **WHEN** 向 `commit` 表写入第二条与已有行相同 `commit_hash` 的记录
- **THEN** 数据库以唯一约束错误拒绝写入，MUST NOT 产生两条同哈希记录

### Requirement: 特征列名与顺序

`commit_feature` 的 14 项特征列名 SHALL 与 `docs/model/feature-columns.md`（契约二）§3 逐字一致；后端组装模型输入向量时 SHALL 按 §3 的列顺序取值，MUST NOT 依赖字典插入顺序或文件列顺序。

#### Scenario: 特征列名对齐

- **WHEN** 将特征表列名与契约二 §3 逐字段比对
- **THEN** 14 项特征列名逐字一致，无大小写或后缀差异

#### Scenario: 特征行缺失

- **WHEN** 特征 CSV 缺少某个 `commit_hash` 的特征行
- **THEN** 灌入报告缺失清单与条数，MUST NOT 静默补 0

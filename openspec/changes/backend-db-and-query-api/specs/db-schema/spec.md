## Purpose

把契约一的表结构落地为可执行建库与灌入，为查询接口与模型线交付物（裁定 C）提供唯一数据落点。

## ADDED Requirements

### Requirement: 建表字段逐字对齐契约

系统 SHALL 按 `docs/contracts/data-fields.md` 表一/二/三建立 `commit`、`commit_label`、`prediction` 三张表：列名逐字一致、一律 snake_case、时间字段统一 UTC 且以 `_at` 结尾；`commit_hash` SHALL 建唯一索引，`committed_at` SHALL 建普通索引。

#### Scenario: 列名逐字对齐

- **WHEN** 将建库产物的列名与类型同契约表一/二/三逐字段比对
- **THEN** 无缺列、无改名列、无自造列

#### Scenario: 重复提交被唯一索引拒绝

- **WHEN** 向 `commit` 表写入第二条与已有行相同 `commit_hash` 的记录
- **THEN** 数据库以唯一约束错误拒绝写入，MUST NOT 产生两条同哈希记录

### Requirement: 一条命令建库

系统 SHALL 提供单条命令在干净 clone 的环境下完成建库，并 SHALL 把该命令写进 `backend/README.md`。

#### Scenario: 干净环境建库

- **WHEN** 在完成 `pip install -r backend/requirements.txt` 与 `.env` 配置的环境执行建库命令
- **THEN** 三张表（及裁定建表后的特征表）创建完成，命令退出码为 0

#### Scenario: 连接配置错误

- **WHEN** `.env` 中数据库地址或凭据错误导致建库失败
- **THEN** 报错信息指出出错的配置项名，MUST NOT 在输出中回显密码明文

### Requirement: 预测结果灌入

系统 SHALL 提供灌入脚本，读取模型线产出的 `prediction_result.csv` 写入 `prediction` 表（交付裁定 C），字段映射照契约一表三；灌入 SHALL 按 `(commit_hash, model_name, feature_version)` 幂等。

#### Scenario: 正常灌入

- **WHEN** 对一份格式正确的 `prediction_result.csv` 执行灌入
- **THEN** `prediction` 表行数与文件行数一致，`risk_score` 逐行与文件一致

#### Scenario: 同一文件重复灌入

- **WHEN** 对同一份文件连续执行两次灌入
- **THEN** 表行数不变，MUST NOT 产生重复行

#### Scenario: 行缺主键字段

- **WHEN** 文件中存在缺失 `commit_hash` 的行
- **THEN** 灌入失败退出并报告行号，本次灌入已写入的行全部回滚

### Requirement: 特征数据落库

（前置：待决问题 1 裁定为建表；否则本 Requirement 随 change 更新删除）系统 SHALL 按契约一 ER 图建立 `commit_feature` 表并灌入数据线产出的特征 CSV；14 项特征列名 SHALL 与 `docs/contracts/feature-columns.md` 逐字一致。

#### Scenario: 特征列名对齐

- **WHEN** 将特征表列名与契约二逐字段比对
- **THEN** 14 项特征列名逐字一致，无大小写或后缀差异

#### Scenario: 特征行缺失

- **WHEN** 特征 CSV 缺少某个 `commit_hash` 的特征行
- **THEN** 灌入报告缺失清单与条数，MUST NOT 静默补 0

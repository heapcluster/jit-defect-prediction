# db-schema Specification

## Purpose
把 `docs/database/` 的五张表及 14 维特征列序落地为可执行建库与实时同步入库，为查询接口、在线预测和模型图集提供数据落点。

## Requirements

### Requirement: 建表字段逐字对齐契约

系统 SHALL 按 `docs/database/` 建立 `commit`、`model`、`commit_feature`、`prediction`、`model_figure` 五张表；`commit_label` 已并入 `commit_feature.is_bug_inducing`，MUST NOT 再建独立表。列名逐字一致、一律 snake_case、时间字段统一 UTC 且以 `_at` 结尾；`commit_hash` SHALL 为主键，`committed_at` SHALL 建索引；五张表 SHALL 由 `infra/schema.sql` 与后端 ORM 的等价结构建立。

#### Scenario: 列名逐字对齐

- **WHEN** 将建库产物的列名与类型同 `docs/database/` 五张表及 14 维列序逐字段比对
- **THEN** 无缺列、无改名列、无自造列

#### Scenario: 重复提交被唯一索引拒绝

- **WHEN** 向 `commit` 表写入第二条与已有行相同 `commit_hash` 的记录
- **THEN** 数据库以唯一约束错误拒绝写入，MUST NOT 产生两条同哈希记录

### Requirement: 一条命令建库

系统 SHALL 提供单条命令在干净 clone 的环境下完成建库，并 SHALL 把该命令与「数据由实时同步产出、需先配置本地历史索引（`SOURCE_REPO`）」的前提写进 `docs/common/local-runbook.md`。

#### Scenario: 干净环境建库

- **WHEN** 在完成 `conda env create -f data_model/environment.yml` 与 `.env` 配置的环境执行建库命令
- **THEN** 五张表创建完成，命令退出码为 0

#### Scenario: 连接配置错误

- **WHEN** `.env` 中数据库地址或凭据错误导致建库失败
- **THEN** 报错信息指出出错的配置项名，MUST NOT 在输出中回显密码明文

### Requirement: 特征列名与顺序

`commit_feature` 的 14 项特征列名 SHALL 与 `docs/database/commit_feature.md` 及 `data_model/pipelines/expert/models/feature_order.txt` 逐字一致；后端组装 expert 模型输入向量时 SHALL 按交付清单列序取值，MUST NOT 依赖字典插入顺序或文件列顺序。

#### Scenario: 特征列名对齐

- **WHEN** 将特征表列名与当前 14 维交付清单逐字段比对
- **THEN** 14 项特征列名逐字一致，无大小写或后缀差异

#### Scenario: 特征行缺失

- **WHEN** 某条提交在实时同步中特征现算失败
- **THEN** 该条计入 `skipped` 并记录原因，MUST NOT 写入缺列或补 0 的特征行，MUST NOT 影响其余提交

### Requirement: 实时同步入库

运行时同步 SHALL 使用 `POST /api/sync`，单条现算 SHALL 使用 `POST /api/predict`；离线测试集可由 `data_model/evaluation/out/data_init.sql` 在测试环境初始化，MUST NOT 冒充实时同步结果。幂等键为 `commit.commit_hash`、`commit_feature.commit_hash`、`prediction.(commit_hash, model_name)`、`model.model_name` 和 `model_figure.(model_name, figure_type)`：同一键重复写入 MUST NOT 产生第二行。同步逐条处理时，单条预测失败 SHALL 计入 `skipped`，不影响其余提交。

#### Scenario: 正常入库

- **WHEN** 对一条可现算特征的提交执行同步预测
- **THEN** 对应模型的预测行按幂等键写入 `prediction` 表，关键字段与现算结果一致

#### Scenario: 同一提交重复同步

- **WHEN** 对同一提交连续执行两次同步预测
- **THEN** `prediction` 表行数不变，MUST NOT 产生重复行

#### Scenario: 单条失败不中断（边界场景）

- **WHEN** 某条提交的特征现算或模型推理失败
- **THEN** 该条计入 `skipped` 并记录原因，其余提交继续写入，整批响应仍为 `code=0`

#### Scenario: 初始化脚本不得冒充服务端入口（边界场景）

- **WHEN** 审查离线测试数据初始化脚本
- **THEN** 它只能在明确的测试/演示初始化流程中运行，MUST NOT 被查询 API 或服务启动流程悄悄调用

#### Scenario: 空库首启（边界场景）

- **WHEN** 干净环境首次启动、五表为空
- **THEN** 查询端点返回空列表（`code=0`）而非 50000；用户从界面触发同步后，提交按「现算特征 → 预测 → 逐条落库」进来，MUST NOT 预先批量灌库

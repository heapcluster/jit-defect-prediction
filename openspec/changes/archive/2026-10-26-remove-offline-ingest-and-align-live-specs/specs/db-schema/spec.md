## REMOVED Requirements

### Requirement: 四份 CSV 灌入

**Reason**: 2026-10-25 裁定彻底移除离线 CSV 灌库 —— `backend/app/ingest.py` 与 `backend/tests/test_ingest.py` 已删除，灌库脚本与其 CLI 入口不再存在，规格继续描述该功能会给出「照此执行即失败」的指令。数据入口统一为实时同步（见新增 Requirement）。

**Migration**: 数据入库改走 `POST /api/sync`（主干新提交）与 `POST /api/sync-prs`（open PR）；历史 CSV 产物只作数据线归档，不再进入运行时。

## MODIFIED Requirements

### Requirement: 一条命令建库

系统 SHALL 提供单条命令在干净 clone 的环境下完成建库，并 SHALL 把该命令与「数据由实时同步产出、需先配置本地历史索引（`SOURCE_REPO`）」的前提写进 `backend/README.md`。

#### Scenario: 干净环境建库

- **WHEN** 在完成 `conda env create -f data_model/environment.yml` 与 `.env` 配置的环境执行建库命令
- **THEN** 四张表创建完成，命令退出码为 0

#### Scenario: 连接配置错误

- **WHEN** `.env` 中数据库地址或凭据错误导致建库失败
- **THEN** 报错信息指出出错的配置项名，MUST NOT 在输出中回显密码明文

### Requirement: 特征列名与顺序

`commit_feature` 的 14 项特征列名 SHALL 与 `docs/model/feature-columns.md`（契约二）§3 逐字一致；后端组装模型输入向量时 SHALL 按 §3 的列顺序取值，MUST NOT 依赖字典插入顺序或文件列顺序。

#### Scenario: 特征列名对齐

- **WHEN** 将特征表列名与契约二 §3 逐字段比对
- **THEN** 14 项特征列名逐字一致，无大小写或后缀差异

#### Scenario: 特征行缺失

- **WHEN** 某条提交在实时同步中特征现算失败
- **THEN** 该条计入 `skipped` 并记录原因，MUST NOT 写入缺列或补 0 的特征行，MUST NOT 影响其余提交

## ADDED Requirements

### Requirement: 实时同步入库

系统 SHALL 只以实时同步端点（`POST /api/sync` 与 `POST /api/sync-prs`）作为数据入库入口，MUST NOT 保留离线 CSV 灌库路径。写入 SHALL 遵循 design D4 的按表幂等键（`commit` 按 `commit_hash`、`commit_label` 按 `(commit_hash, label_method)`、`commit_feature` 按 `commit_hash`、`prediction` 按 `(commit_hash, model_name)`）：同一键重复写入 MUST NOT 产生第二行。同步逐条处理时，单条预测失败 MUST 只影响该条并计入 `skipped`，MUST NOT 中断整批，MUST NOT 使整端返回 50000。

#### Scenario: 正常入库

- **WHEN** 对一条可现算特征的提交执行同步预测
- **THEN** 对应模型的预测行按幂等键写入 `prediction` 表，关键字段与现算结果一致

#### Scenario: 同一提交重复同步

- **WHEN** 对同一提交连续执行两次同步预测
- **THEN** `prediction` 表行数不变，MUST NOT 产生重复行

#### Scenario: 单条失败不中断（边界场景）

- **WHEN** 某条提交的特征现算或模型推理失败
- **THEN** 该条计入 `skipped` 并记录原因，其余提交继续写入，整批响应仍为 `code=0`

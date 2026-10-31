# nfr-evidence Specification

## Purpose
把课程两项非功能要求（性能、安全）变成可复跑、可出示的证据：分位数压测与两组安全用例，证据进仓库并标注模型来源。

## Requirements

### Requirement: 性能压测脚本

交付验收 SHALL 提供可复现的压测命令或脚本：对 `POST /api/predict` 循环发送 100 次请求，输出 p50 / p95 / p99 与最大值，MUST NOT 以平均值代替分位数；输出 SHALL 标注目标「p95 < 500ms」与实际达标判定。旧 `backend/scripts/` 入口已从仓库移除；当前必须重新提供可运行入口和实际日志，未提供前不得标为通过。

#### Scenario: 正常输出分位数

- **WHEN** 服务可达且模型已加载时运行脚本
- **THEN** 输出包含 100 次请求的 p50/p95/p99/最大值与达标判定（达标/未达标）

#### Scenario: 服务不可达

- **WHEN** BASE_URL 不可达或鉴权失败时运行脚本
- **THEN** 脚本以非零退出码失败并说明原因，MUST NOT 产出任何伪造的分位数输出

### Requirement: 安全用例脚本

交付验收 SHALL 提供可复现的安全用例入口，覆盖并断言：① 缺失令牌与错误令牌均返回 HTTP 401 且 `code=40100`、message 为 `missing or invalid token`；② 畸形参数（`size=101`、`granularity=day`、非 40 位十六进制 hash）返回 40001 且响应体不含异常堆栈、SQL 语句、文件路径关键字；③ 模型缺失时 `POST /api/predict` 返回 50000 且 message 为固定文案、不含路径。旧安全脚本已从仓库移除，须在新入口实测后登记结果。

#### Scenario: 全部用例通过

- **WHEN** 对运行中的服务执行脚本
- **THEN** 输出逐用例 PASS/FAIL 与汇总，全部通过时退出码为 0

#### Scenario: 任一断言失败

- **WHEN** 任一用例断言不成立
- **THEN** 脚本以非零退出码结束并列出失败用例与实际响应，MUST NOT 汇总为通过

### Requirement: 证据留档与占位模型标注

每次运行 SHALL 保存可点开的证据记录，含运行日期、模型来源标注（占位模型 / 真模型及 model_name）、可复现命令与关键输出；占位模型证据 SHALL 显式标注「占位模型」，真 `.pkl` 交付后 SHALL 重跑并附新证据。已删除的历史文件不能作为当前可点证据。

#### Scenario: 证据文件含模型来源行

- **WHEN** 任一脚本运行完成
- **THEN** 对应证据记录中存在「模型来源」行，占位运行时值为「占位模型（待真 .pkl 重跑）」

#### Scenario: 真模型重跑追加

- **WHEN** 真 `.pkl` 交付后重跑压测
- **THEN** 新增一份带真模型标注的证据记录，并保留原占位记录的可追溯链接

## Purpose

把课程两项非功能要求（性能、安全）变成可复跑、可出示的证据：分位数压测与两组安全用例，证据进仓库并标注模型来源。

## ADDED Requirements

### Requirement: 性能压测脚本

系统 SHALL 提供 `backend/scripts/perf_loop.py`：对 `POST /api/predict` 循环发送 100 次请求，输出 p50 / p95 / p99 与最大值，MUST NOT 以平均值代替分位数；输出 SHALL 标注目标「p95 < 500ms」与实际达标判定。

#### Scenario: 正常输出分位数

- **WHEN** 服务可达且模型已加载时运行脚本
- **THEN** 输出包含 100 次请求的 p50/p95/p99/最大值与达标判定（达标/未达标）

#### Scenario: 服务不可达

- **WHEN** BASE_URL 不可达或鉴权失败时运行脚本
- **THEN** 脚本以非零退出码失败并说明原因，MUST NOT 产出任何伪造的分位数输出

### Requirement: 安全用例脚本

系统 SHALL 提供 `backend/scripts/security_cases.py`，覆盖两组用例并断言：① 缺失令牌与错误令牌均返回 HTTP 401 且 `code=40100`、message 为 `missing or invalid token`；② 畸形参数（`size=101`、`granularity=day`、非 40 位十六进制 hash）返回 40001 且响应体不含异常堆栈、SQL 语句、文件路径关键字；③ 模型缺失时 `POST /api/predict` 返回 50000 且 message 为固定文案、不含路径。

#### Scenario: 全部用例通过

- **WHEN** 对运行中的服务执行脚本
- **THEN** 输出逐用例 PASS/FAIL 与汇总，全部通过时退出码为 0

#### Scenario: 任一断言失败

- **WHEN** 任一用例断言不成立
- **THEN** 脚本以非零退出码结束并列出失败用例与实际响应，MUST NOT 汇总为通过

### Requirement: 证据留档与占位模型标注

每次运行 SHALL 产出 `backend/scripts/evidence/<日期>-<主题>.md`，含运行日期、模型来源标注（占位模型 / 真模型及 model_name）、命令与关键输出，并提交版本控制；占位模型证据 SHALL 显式标注「占位模型」，真 `.pkl` 交付后 SHALL 重跑并追加新证据，旧证据保留不删。

#### Scenario: 证据文件含模型来源行

- **WHEN** 任一脚本运行完成
- **THEN** 对应证据 md 中存在「模型来源」行，占位运行时值为「占位模型（待真 .pkl 重跑）」

#### Scenario: 真模型重跑追加

- **WHEN** 真 `.pkl` 交付后重跑压测
- **THEN** 新增一份带真模型标注的证据 md，原占位证据文件保留在 evidence/ 目录

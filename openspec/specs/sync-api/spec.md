# sync-api Specification

## Purpose

规定批量同步的当前 HTTP 入口和异步状态口径；参数与响应字段以 `docs/api/sync.md` 为准。

## Requirements

### Requirement: 按范围异步补算

`POST /api/sync` SHALL 接受可选 `line`、`model_name`、`start_time`、`end_time`，按目标模型缺失的预测行补算；未指定模型时目标为全部在线模型。请求 SHALL 异步返回，逐条完成情况由 `GET /api/sync/status` 查询。MUST NOT 把旧的 `limit=N` 当作当前公开契约。

#### Scenario: 指定模型补算

- **WHEN** 请求指定有效 `model_name` 且时间范围内有缺该模型预测的提交
- **THEN** 系统接受任务，并只补目标模型缺失的行；同键重试不产生重复行

#### Scenario: 模型参数非法

- **WHEN** 请求的 `line` 或 `model_name` 不属于可接受集合
- **THEN** 返回 40001，MUST NOT 悄悄改为其他模型或全模型同步

### Requirement: 状态轮询与并发限制

`GET /api/sync/status` SHALL 返回 `running`、`total`、`done`、`current_hash`、`last_error` 等本进程任务快照；同一时刻只允许一个同步任务。状态只在内存中，进程重启后 MUST NOT 冒充历史执行记录。

#### Scenario: 同步进行中

- **WHEN** 一个同步任务正在处理提交
- **THEN** 状态接口报告 `running=true` 与当前进度，前端可据此轮询

#### Scenario: 重复触发

- **WHEN** 前一个同步任务未结束又收到第二次触发
- **THEN** 第二次请求按 `docs/api/sync.md` 的并发错误口径返回，MUST NOT 开始第二个并行写入任务

# user

`实现状态：部分　期次：一期`

W1 已实现迁移预置 global 与配置服务的归属/禁用校验；一期固定 API Token 接口默认操作 global，不新增登录注册或用户管理界面。

**一句话**：系统用户表，一行对应一个可持有配置的操作者；与 `commit.author_name / author_email`（提交作者）是完全不同的概念，MUST NOT 混用。

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| user_id | VARCHAR(36) | NOT NULL | 主键 | 用户标识；预置全局行 `global` |
| display_name | VARCHAR(64) | NOT NULL | — | 显示名 |
| role | VARCHAR(16) | NOT NULL DEFAULT 'member' | — | `system` / `admin` / `member` |
| status | VARCHAR(16) | NOT NULL DEFAULT 'active' | — | `active` / `disabled` |
| created_at | DATETIME | NOT NULL | — | 创建时间 |

## 主键与约束理由

- `user_id` 自然主键（UUID 字符串），`user_config` 外键指向它。
- 预置行 `user_id='global'`、`role='system'`：无登录上下文时的配置归属；建表脚本以 `INSERT IGNORE` 预置，重复执行幂等（infra/schema.sql）。
- 本表不存任何凭证列：口令、API Key 等敏感信息 MUST NOT 入库。
- 认证沿用 `X-API-Key` 固定令牌；一期不做登录注册产品化、权限审批流与多租户隔离（设计图功能 ① 范围界定）。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 建表脚本预置 `global` 行；管理接口创建用户 | 配置归属 |
| 读取 | 配置服务（解析当前用户 → 缺省 `global`） | 配置读写归属判定 |
| 展示 | 设置页（常用全局配置） | 单页简单表单，不展示配置归属来源 |

## 口径

- `disabled` 用户的配置读取返回明确错误码，不静默回退全局行。
- 一期角色只做标识，不做权限审批流。
- 提交作者信息在 `commit` 表，与本表无外键关系。

## 验收

- 空库执行建表脚本后 `global` 行存在；重复执行不产生重复行。
- 创建用户 → 保存配置 → 重启后端 → 配置仍按该用户恢复。
- 表内无凭证列；接口不回显任何敏感字段。
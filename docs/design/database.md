# 数据库设计（四张表）

> 合并自原 `docs/dev-handbook.md` §7（已并入 common/dev-handbook.md）+ 契约一（已并入本文件 data-fields.md） ｜ 审核：吕建江、蒋励
> 课程要求「数据库设计，确定表结构」。ER 图源在契约（鸦爪法），飞书设计文档引用同一张，不各画。

## 1. 四张表

### commit（提交主表）
| 字段 | 类型 | 说明 |
|---|---|---|
| `commit_hash` | CHAR(40) PK | 提交哈希 |
| `repo_name` | VARCHAR | 固定 `camel` |
| `author_name` | VARCHAR | 作者 |
| `committed_at` | DATETIME | 提交时间（UTC，不加 Z） |
| `message` | TEXT | 提交信息 |

索引：`commit_hash` 唯一；`committed_at` 普通。

### commit_label（打标结果）
| 字段 | 类型 | 说明 |
|---|---|---|
| `commit_hash` | CHAR(40) | 外键 commit |
| `label_method` | ENUM('szz','szz_lite') | 打标方法 |
| `is_bug_inducing` | TINYINT | 1=引入缺陷 |

PK 复合 `(commit_hash, label_method)`；一个提交可两方法各行。

### commit_feature（14 项特征）⚠️ 最易漏
| 字段 | 类型 | 说明 |
|---|---|---|
| `commit_hash` | CHAR(40) PK | 外键 commit |
| `ns,nd,nf,entropy,la,ld,lt,fix,ndev,age,nuc,exp,rexp,sexp` | DOUBLE | Kamei 14 项（口径处理后值） |

键名必须与 `feature-columns.md` 一致；提交详情接口必须读它取 14 项特征。

### prediction（预测结果）
| 字段 | 类型 | 说明 |
|---|---|---|
| `commit_hash` | CHAR(40) | 外键 commit |
| `model_name` | VARCHAR | 模型版本 |
| `risk_score` | DOUBLE | 风险概率 0~1 |
| `predicted_at` | DATETIME | 预测时间（UTC） |

PK 复合 `(commit_hash, model_name)`；A（实时推理）与实时同步**写同一张表**，靠 `model_name` 区分；幂等 upsert（入库只走实时同步端点，无离线 CSV 灌库）。

## 2. ER 图（鸦爪法）

```mermaid
erDiagram
  commit ||--o{ commit_label : "1 提交多方法标签"
  commit ||--o| commit_feature : "1 提交 14 特征"
  commit ||--o{ prediction : "1 提交多模型预测"
  commit_label { commit_hash PK, label_method, is_bug_inducing }
  commit_feature { commit_hash PK, ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp }
  prediction { commit_hash PK, model_name PK, risk_score, predicted_at }
```

> 生成方式：Mermaid `erDiagram` ｜ 提示词：「画 commit/commit_label/commit_feature/prediction 四表 ER，commit_label 与 prediction 复合主键，鸦爪法」

## 3. 建表要求

- Alembic 或 SQL 脚本均可，但别人 `clone` 后**一条命令建好库**。
- 字段名、类型、索引与契约一逐字一致（含 `commit_feature`）。
- `50000` 的 message 不回显堆栈/SQL/路径。

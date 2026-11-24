# commit_feature

`实现状态：已实现　期次：一期`

**一句话**：一行对应一次提交的 Kamei 14 维特征 + `is_test` 切分标记 + SZZ 真标签；是模型输入，也是提交详情与模型性能看板「特征列 + 真标签」的唯一来源。

实现锚点：backend/app/models.py:61-85

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| commit_hash | CHAR(40) | NOT NULL | 主键 + 外键 → `commit.commit_hash` | 与 `commit` 严格 1:1 |
| feature_version | VARCHAR(32) | NOT NULL | — | 特征版本，`v1` = Kamei 14 维 |
| ns | DECIMAL(20,10) | NOT NULL | — | `ln(本次修改涉及的文件数)` |
| nd | DECIMAL(20,10) | NOT NULL | — | `ln(本次修改涉及的目录数)` |
| nf | DECIMAL(20,10) | NOT NULL | — | `ln(本次修改的文件总数)` |
| entropy | DECIMAL(20,10) | NOT NULL | — | `ln(修改在文件间分布的熵)` |
| la | DECIMAL(20,10) | NOT NULL | — | `ln(la / lt)`：新增行占改动总量的比例取对数 |
| ld | DECIMAL(20,10) | NOT NULL | — | `ln(ld / lt)`：删除行占改动总量的比例取对数 |
| lt | DECIMAL(20,10) | NOT NULL | — | `ln(lt / nf)`：单文件平均改动量取对数 |
| fix | TINYINT(1) | NOT NULL | — | 是否修复提交（0/1），唯一不取对数的特征 |
| ndev | DECIMAL(20,10) | NOT NULL | — | `ln(曾修改过这些文件的开发者总数)` |
| age | DECIMAL(20,10) | NOT NULL | — | `ln(文件自创建至今的存在时长)` |
| nuc | DECIMAL(20,10) | NOT NULL | — | `ln(nuc / nf)`：这些文件的既往改动次数按文件数归一后取对数 |
| exp | DECIMAL(20,10) | NOT NULL | — | `ln(作者历史提交数)` |
| rexp | DECIMAL(20,10) | NOT NULL | — | `ln(作者近期提交数，按时间衰减加权)` |
| sexp | DECIMAL(20,10) | NOT NULL | — | `ln(作者在这些文件上的专属经验)` |
| is_test | TINYINT(1) | NOT NULL DEFAULT 0 | ix_commit_feature_is_test | 是否检验集（时间序后 30%），`1` = 测试集 |
| is_bug_inducing | TINYINT(1) | 可空 | — | SZZ 真标签：`1` = 引入缺陷 / `0` = 非缺陷 / `NULL` = 未打标 |
| labeled_at | DATETIME | 可空 | — | SZZ 批量打标时间（审计列，不对外） |

## 主键与约束理由

- 主键 = `commit_hash`（兼外键），与 `commit` 严格 1:1，一个提交一行特征。
- `is_test` 单列索引：模型性能评估按 `is_test = 1` 全量筛检验集。
- 14 维列序即交付列序：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp`，与 `data_model/pipelines/expert/models/feature_order.txt` 一致。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 收集 / 清洗服务、预测服务现算特征（插件复用 `03_extract_features.py`）、切分与打标产物导入 | 特征、`is_test`、真标签落库 |
| 读取 | predict（组装 14 维输入向量）、commits（列表特征列、详情特征与真标签）、evaluate（join 取真标签算指标） | 推理与评估 |
| 展示 | 提交详情（14 维 + 真标签）、模型性能看板（检验集特征列 + SZZ 判断） | 可读特征与真值 |

## 口径

- **log 变换**：除 `fix` 外全部落库值都是对数变换后的值，不是原始计数 / 行数。变换定义在 `data_model/preparation/03_extract_features.py` 的 `log_v1` + `apply_contract`：
  - `log_v1(x) = ln(x)`（`x > 0`）；`x == 0` 记 `0`。该契约在 0 附近不连续，按字面实现，不擅自修正。
  - `la / ld` 先算占改动总量 `lt` 的比例，`lt / nuc` 先按 `nf` 归一，再取对数；其余各项对原值取 `ln`。
- **时间方向**：历史类特征（`ndev / age / nuc / exp / rexp / sexp`）只使用严格早于本次提交的提交计算；`lt` 取父提交时刻的文件行数。`rexp` 衰减口径 `Σ count(n)/(n+1)`，`n` 为历史提交距本次提交的整年数；`nuc` 按文件分别计既往改动次数再求和（与 `ndev` 数「人」去重故意不对称）。
- **展示口径**：详情与性能表的特征是 log 值（可为负）。MUST NOT 把 log 值当原始计数展示；可读原值语义由展示层做 `exp` 还原或改用贡献度表述，契约层不做还原。
- **只承载 Kamei 14 维**这一层可解释特征；语义 768 维、融合 782 维、e2e 文本不落关系表。四线提交都抽这 14 维（性能表对四线展示特征列），但只有 expert 线把它当模型输入。
- **`is_test`**：按 `commit.committed_at` 时间序前 70% / 后 30% 切分（默认比例，可配置）；禁止随机切分；切分 MUST 保留「检验集最早时间 > 训练集最晚时间」断言。`is_test` 只是切分结果落库，不是另一种切分口径。
- **`is_bug_inducing`**：训练主标签为 `szz`；未打标提交保持 `NULL`，MUST NOT 当 `0` 使用或计入负样本。`labeled_at` 是审计列，不对外；同一批打标整列同值，不能当「缺陷发生 / 修复时间」展示。
- `is_test` / `is_bug_inducing` / `labeled_at` 与 14 维特征同版本（`feature_version`）。

## 验收

- 落库值与 `apply_contract` 输出逐列一致；`fix` 为 0/1，其余 13 列为 log 值。
- 未打标提交的 `is_bug_inducing` 返回 `NULL`，任何统计不得把它计入负样本。
- `is_test = 1` 筛选走索引；检验集最早时间晚于训练集最晚时间。
- 列序与 `feature_order.txt` 一致，特征版本随产物写入。

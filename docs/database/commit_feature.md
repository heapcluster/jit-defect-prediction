# commit_feature（复用表）

**一句话**：一行对应一次提交的 **Kamei 14 维特征 + `is_test` 切分标记 + SZZ 真标签**；是模型输入，也是提交详情与模型性能看板「特征列 + 真标签」的唯一来源。

## 字段

| 字段 | 类型 | 键 | 含义 |
|---|---|---|---|
| commit_hash | CHAR(40) | 主键 + 外键 → `commit.commit_hash` | 与 `commit` 1:1，直接拿它做 PK |
| feature_version | VARCHAR(32) | — | 特征版本，`v1` = Kamei 14 维 |
| ns | DECIMAL(20,10) | — | `ln(本次修改涉及的文件数)` |
| nd | DECIMAL(20,10) | — | `ln(本次修改涉及的目录数)` |
| nf | DECIMAL(20,10) | — | `ln(本次修改的文件总数)` |
| entropy | DECIMAL(20,10) | — | `ln(修改在文件间分布的熵)` |
| la | DECIMAL(20,10) | — | `ln(la / lt)`：新增行占改动总量的比例取对数 |
| ld | DECIMAL(20,10) | — | `ln(ld / lt)`：删除行占改动总量的比例取对数 |
| lt | DECIMAL(20,10) | — | `ln(lt / nf)`：单文件平均改动量取对数 |
| fix | TINYINT(1) | — | 是否为修复提交（0/1），**唯一不取对数的特征** |
| ndev | DECIMAL(20,10) | — | `ln(曾修改过这些文件的开发者总数)` |
| age | DECIMAL(20,10) | — | `ln(文件自创建至今的存在时长)` |
| nuc | DECIMAL(20,10) | — | `ln(nuc / nf)`：近期修改这些文件的开发者数按文件数归一后取对数 |
| exp | DECIMAL(20,10) | — | `ln(作者历史提交数)` |
| rexp | DECIMAL(20,10) | — | `ln(作者近期提交数)` |
| sexp | DECIMAL(20,10) | — | `ln(作者在这些文件上的专属经验)` |
| is_test | TINYINT(1) | 索引 | 是否检验集（时间序后 30%），`1` = 测试集 |
| is_bug_inducing | TINYINT(1) | — | **SZZ 真标签**（`1` = 引入缺陷 / `0` = 非缺陷），**可空**；库内外同名，未打标为 `NULL` |
| labeled_at | DATETIME | — | SZZ 批量打标时间（**审计列，不对外**；同一批打标整列同值） |

## 14 维落库口径（对数变换，MUST 知悉）
- **除 `fix` 外，全部 14 维落库值都是对数变换后的值**，不是原始计数/行数。变换定义在模型线 `data_model/preparation/03_extract_features.py` 的 `apply_contract` + `log_v1`：
  - `log_v1(x) = ln(x)`（`x > 0`）；`x == 0` 时记 `0`（即 `ln(1+0)`，契约本身在 0 附近不连续，脚本不擅自修正）。
  - `la / ld` 先算「占改动总量 `lt` 的比例」，`lt / nuc` 先按 `nf` 归一，**再取对数**。
- **含义**：`ns/nd/nf/entropy/ndev/age/exp/rexp/sexp` 是对原值取 `ln`；`la/ld/lt/nuc` 是先算比值再取 `ln`。
- **前端展示口径**：详情与模型性能表的特征是 log 值（可为负），不是「行数 / 人数」。若要对用户展示可读的原值语义，需在展示层做 `exp` 还原或改用「贡献度」表述；契约层不做还原，MUST NOT 把 log 值当原始计数展示。

## 约束与索引
- 主键 = `commit_hash`（外键），与 `commit` 严格 1:1。
- `is_test` 单列索引：模型性能评估按 `is_test = 1` 全量筛。

## 被谁所用
| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 后端 `sync` / `predict`（现算特征）、模型线交付导入（`is_test` / `is_bug_inducing` / `labeled_at`） | 抽特征落库、切分与打标落库 |
| 读取 | 后端 `commits`（列表 `with_features=1` 的特征列、详情的特征与真标签）、`predict`（组装 14 维输入向量） | 展示与推理 |
| 展示 | 前端提交详情（14 维 + 真标签）、模型性能看板多维表格（测试集特征列 + SZZ 判断） | 可读特征与真值 |

## 口径
- **只承载 Kamei 14 维**这一层可解释特征；语义 768 维、融合 782 维、e2e 文本**不落关系表**。
- 特征抽取是共享上游，四线提交都抽过这 14 维，故模型性能表对四线都展示特征列；但**只有 expert 线把它当模型输入**。
- `is_test`：`1` = 时间序后 30% 测试集，按 `commit.committed_at` 前 70%/后 30% 切（红线：禁止随机切）；`is_test` 只是切分结果落库，不是另一种切分口径。
- **`is_bug_inducing` 由原 `commit_label` 表并入**（`commit_label` 已删除）：
  - `label_method` 恒为 `szz`，列已删除；`bug_fix_hash` 是死字段，已删除；
  - `labeled_at` 保留为审计列，**不对外**；实测同一批打标整列同值，不能当「缺陷发生/修复时间」展示；
  - 库内外统一叫 `is_bug_inducing`，无映射；
  - 该列**可空**：SZZ 只覆盖打标范围内的提交，新同步且尚未打标的提交必须返回 `NULL`，不得默认成 `0`。
- `is_test` / `is_bug_inducing` / `labeled_at` 与 14 维特征同版本（`feature_version`），由模型线切分/打标产物写入。

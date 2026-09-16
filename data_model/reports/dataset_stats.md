# 样本集统计（04_build_dataset.py 产出）—— 第 6 项交付物的证据

> 本文件可入库，七项统计的定义与验收标准见 `docs/data-pipeline.md` 第 6 节

## 七项统计

| 指标 | 值 | 说明 |
|---|---|---|
| 总提交数 | 275 | 过滤合并提交之后的数 |
| 时间跨度 | 2023-01-10 17:29:33 ~ 2025-03-13 13:15:27 | 最早 ~ 最晚提交时间（UTC） |
| 打标成功数（`szz`） | 255 | 能判定标签的提交数；被 D5 排除的修复提交不计入 |
| **正样本数**（`szz`） | 13 | `is_bug_inducing = 1` |
| 负样本数（`szz`） | 242 | `is_bug_inducing = 0` |
| **正样本比例**（`szz`） | **5.10%** | 正样本数 ÷ 打标成功数 |
| 打标成功数（`szz_lite`） | 260 | 能判定标签的提交数；被 D5 排除的修复提交不计入 |
| **正样本数**（`szz_lite`） | 17 | `is_bug_inducing = 1` |
| 负样本数（`szz_lite`） | 243 | `is_bug_inducing = 0` |
| **正样本比例**（`szz_lite`） | **6.54%** | 正样本数 ÷ 打标成功数 |
| 打标方法 | `szz`、`szz_lite` | 见 `contracts/data-fields.md` 表二 |

## 正样本比例是否落在合理区间

判定依据：`docs/data-pipeline.md` 第 6 节 —— 落在 40%–60% 就先查打标逻辑。

- ✅ `szz`：5.10% 不在异常区间（JIT 经验区间为个位数到十几百分点）
- ✅ `szz_lite`：6.54% 不在异常区间（JIT 经验区间为个位数到十几百分点）

## 对齐与断言

| 检查项 | 结果 |
|---|---|
| 断言 A：无「有标签却不在提交清单里」的行 | ✅ 通过（0 条） |
| 断言 B：无「有标签却没有特征」的行 | ✅ 通过（0 条） |
| 样本集不含切分列 | ✅ 通过 |
| 特征表行数（03 产出，含被 D5 排除的提交） | 275 |
| `szz`：提交清单中未进样本的条数 | 20（含回溯未命中被 D5 排除的、以及窗口内未被任何修复提交指控的） |
| `szz_lite`：提交清单中未进样本的条数 | 15（含回溯未命中被 D5 排除的、以及窗口内未被任何修复提交指控的） |

## 产出

- `D:\workspace\code\course\jit-defect-prediction\data_model\data\dataset_window2023_szz.csv` —— 255 行 × 20 列（14 项特征 + 标签），`label_method = szz`
- `D:\workspace\code\course\jit-defect-prediction\data_model\data\dataset_window2023_szz_lite.csv` —— 260 行 × 20 列（14 项特征 + 标签），`label_method = szz_lite`

## 说明

- 样本集**不含任何切分列，也不产出切分文件**：按 `committed_at` 前 70%/后 30% 的时间序切分属下游 change（`AGENTS.md` 禁止随机切分）
- 标签来源：`docs/data-pipeline.md` 第 7 节判据 D4（缺陷编号 且 修复语义双命中）+ 决策 D5（回溯未命中者不入样本、不记 0）
- 特征口径：`docs/contracts/feature-columns.md` 第四节（归一化 + 自然对数变换），版本号见样本集 `feature_version` 列
- 输入文件：`commit_labels_window2023_szz.csv`；`commit_labels_window2023_szz_lite.csv`

# 时间序切分统计（05_split_dataset.py 产出）

> 本文件可入库。切分口径见 `data_model/README.md` 铁规矩 1 与 `docs/contracts/feature-columns.md` 第二节。

## 切分结果

| 项 | 值 |
|---|---|
| 输入样本集 | `data_model\data\dataset_szz_lite.csv` |
| 样本总数 | 10880 |
| 切分比例 | 前 70% 训练 / 后 70% 之外的 30% 检验（按 `committed_at` 升序） |
| 训练集行数 | 7615 |
| 检验集行数 | 3265 |
| 训练集时间范围 | 2005-12-12 17:53:59 ~ 2014-02-10 18:25:47 |
| 检验集时间范围 | 2014-02-10 20:27:35 ~ 2025-03-13 13:15:27 |
| 训练集正样本 | 2346（30.81%） |
| 检验集正样本 | 672（20.58%） |
| 训练/检验时间间隔 | 0.08 天 |

## 断言

| 检查项 | 结果 |
|---|---|
| 检验集最早的 `committed_at` **严格晚于** 训练集最晚的 | ✅ 通过 |
| 行数守恒（训练 + 检验 = 样本集） | ✅ 通过（7615 + 3265 = 10880） |

## 边界场景（tasks.md 3.1 要求留输出）

`python 05_split_dataset.py --selfcheck` —— 把输入**打乱**后走同一条校验（`random.Random(0)`，可复现）：

```
[05] --selfcheck：打乱输入后再切，应当被断言拦下
      [已拦截] 时间序被破坏：检验集最早 <日期> 不晚于训练集最晚 <日期>
[05] 断言工作正常（拦住了乱序输入，未产出文件）
```

> 第一版自检写的是「不排序直接切」，结果**没拦住** —— 因为 04 产出的样本集本身已按
> `committed_at` 升序，前 70% 仍是时间序。**这说明自检本身也要能失败，否则等于没检。**
> 现改为先 `shuffle` 再切。

## 产出

- `D:\workspace\code\course\jit-defect-prediction\data_model\data\split_szz_lite_train.csv`
- `D:\workspace\code\course\jit-defect-prediction\data_model\data\split_szz_lite_test.csv`

两份文件列结构与样本集完全一致（含 `ns` 起 14 项特征 + 标签），**不新增任何切分列** ——
切分结果由文件名区分，样本集本身保持干净。

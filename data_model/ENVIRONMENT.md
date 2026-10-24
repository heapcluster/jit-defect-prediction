# data_model 环境配置与开训说明（另一台电脑开箱即用）

> 适用：数据与模型线（负责人 蒋励）｜ 创建 2026-10-21 ｜ 关联 change：`env-single-source`
> 目标：任何一台机器 `git clone` 后，照本文从零到训出四条线（expert / semantic / fused / e2e）结果。
> **唯一权威环境文件**：`data_model/environment.yml`（仓库内不再有 `requirements.txt`）。

## 0. 前置条件

| 项 | 要求 |
|---|---|
| 系统 | Windows 10/11 或 Linux / WSL |
| Git | 已安装，能访问 GitHub |
| 环境管理 | Miniconda / Anaconda（`conda` 可用） |
| Python | 3.12.x（由 environment.yml 固定） |
| GPU 线 | NVIDIA 驱动（支持 CUDA 12.4）；RTX 4060 即可 |
| 磁盘 | ≥ 5GB（Camel 仓库 + 数据 + 模型）；HF 权重另约 1GB |

> Windows 上若输入 `python` 弹出应用商店，说明 conda 未激活 → 用 **Anaconda Prompt**，或先 `conda init powershell` 再重开终端。

## 1. 拉代码

```bash
git clone <仓库地址> jit-defect-prediction
cd jit-defect-prediction
```

## 2. 创建环境（只用这一份文件）

```bash
conda env remove -n jit-defect-prediction        # 若已存在同名环境
conda env create -f data_model/environment.yml
conda activate jit-defect-prediction
python -V                                        # 必须是 3.12.x
python -c "import torch; print(torch.__version__)"  # 必须 2.5.1；若显示 2.14.1 说明是旧环境，按上一行 remove 后重建
```

> 若已在 `data_model/` 目录，等价命令：`conda env create -f environment.yml`。

## 3. GPU（4060）必做：装 CUDA 版 torch

PyPI 的 `torch==2.5.1` 是 CPU 版，创建环境后必须替换为 CUDA 版：

```bash
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124
```

验证：

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# 期望：2.5.1+cu124 True NVIDIA GeForce RTX 4060

python -c "import pandas,numpy,sklearn,xgboost,lightgbm,shap,transformers,matplotlib; print('stack ok')"
# 期望：stack ok
```

CPU 机器可跳过本步，但 semantic 会很慢、e2e 无法实际训练。

## 4. 数据准备（`data/` 不入库）

`data_model/data/` 被 `.gitignore` 排除（含 Camel 仓库副本、中间数据、切分文件）。二选一：

**A. 从已有机器整体拷贝** `data_model/data/`（最快，含全部中间产物）。

三条线实际依赖的文件见各包 `config.py`，最小可用清单只有 4 个（合计约 64MB，zip 后约 22MB，可直接飞书发送）：

| 文件 | 大小 | 谁用 |
|---|---|---|
| `split_szz_train.csv` / `split_szz_test.csv` | 16.3 / 6.9 MB | 四条线共用（`TRAIN_CSV` / `TEST_CSV`） |
| `commit_features_raw.csv` | 14.8 MB | Effort-aware 的 LOC 工作量代理（`la + ld`） |
| `dataset_szz.csv` | 26.4 MB | semantic / e2e 自建 diff 文本时的标签与提交清单；`e2e/build_text_dataset.py` 的 `--dataset`、`semantic/data.py::extract_texts_from_repo` 都**必读**，缺失直接退出码 2 |
> 这四个 CSV 只解决**上游数据**，不等于可以开训四条线：e2e / semantic 若要自建 diff 文本，
> 还需要 Camel 克隆（`--repo` 指向它，固定 `b2329103…`）；否则得直接复用现成的
> `pipelines/e2e/data/commit_text.csv`（该文件同样不入库，需一并拷贝）。

拷贝后按哈希核对（2026-10-23 实测快照）：

| 文件 | SHA256（前 32 位） |
|---|---|
| `split_szz_train.csv` | `E40AF1FB1AE354CE70038352B7D2BD44` |
| `split_szz_test.csv` | `35E7C82512E873F5D1D1DBBE5A2AF47B` |
| `commit_features_raw.csv` | `8E4DD28AA58F9962FB1AF48C23D29EB0` |
| `dataset_szz.csv` | `735903F1BD74412B66477E817D933A51` |

> 大小与行数只能做粗略的传输检查，**不能**据此断言“SZZ 未重跑”——同样大小也可能是不同内容。
> 哈希一致才说明是同一份数据；若你自己重跑 01–05，哈希本就会变，需在 `docs/model/data-pipeline.md` 重新登记。

**B. 从零重跑 01–05**（干净复现）：

```bash
cd data_model
# 克隆 Apache Camel 并切到固定版本（命令见 docs/model/data-pipeline.md 第 2 节）
git -C data/camel rev-parse HEAD
# 必须等于：b2329103df8f5d1edfca2ad262be09e3be95ee68

python preparation/01_extract_commits.py
python preparation/02_szz_labeling.py --method both
python preparation/03_extract_features.py
python preparation/04_build_dataset.py --labels data/commit_labels_szz.csv --labels data/commit_labels_szz_lite.csv
python preparation/05_split_dataset.py --tag szz
```

## 5. 训练（全部在 `data_model/` 下，按依赖跑序）

| 步骤 | 线路 | 命令 | GPU |
|---|---|---|---|
| 1 | expert（基线） | `python -m pipelines.expert.train` | 否 |
| 2 | semantic（语义，**先跑**） | `python -m pipelines.semantic.train --repo data/camel` | 建议 |
| 3 | fused（融合，**吃 semantic 缓存**） | `python -m pipelines.fused.train` | 否 |
| 4 | e2e（端到端微调） | `python -m pipelines.e2e.build_text_dataset` 然后 `python -m pipelines.e2e.train` | **必须** |

补充命令：

```bash
# expert 全量推理 / 覆盖矩阵 / 校准（CPU）
python -m pipelines.expert.predict
python -m pipelines.expert.matrix
python -m pipelines.expert.calibrate

# semantic：复用 e2e 文本，或只训子集冒烟
python -m pipelines.semantic.train --text-csv pipelines/e2e/data/commit_text.csv
python -m pipelines.semantic.train --models lr

# e2e：冒烟 / 显存不足
python -m pipelines.e2e.train --epochs 1
python -m pipelines.e2e.train --batch-size 8
```

**跑序依赖**：expert 独立；semantic 必须在 fused 之前（fused 吃 `semantic/data/semantic_embeddings.npz`）；e2e 独立（吃文本）。
**分类器数量**以各包 `config.py` 的 `DEFAULT_MODELS` 为准：`expert` / `semantic` / `fused` 的**训练口径为 8 个**（`lr rf xgb lgbm et svm mlp_deep tabnet`）；`model.py` 的 `MODEL_NAMES` 注册表仍是 12 个（多出 `nb dt knn mlp`，仅兼容旧产物、默认不训练），由 `data_model/tests/test_model_registry_parity.py` 守护三线一致；`e2e` 为单个 CodeBERT 二分类头。训练口径变更见 `openspec/changes/model-training-scope-8/`。

## 6. 产物：哪些进仓库、哪些不进

| 路径 | 内容 | 入库 |
|---|---|---|
| `pipelines/<line>/reports/*.md` | 指标报告 | ✅ **必须提交** |
| `pipelines/<line>/reports/figs/*.png` | 图表 | ✅ **必须提交** |
| `pipelines/*/models/feature_order.txt`、`manifest.txt` | 交付清单（纯文本） | ✅ 提交 |
| `*.pkl / *.joblib / *.pt / *.pth / *.ckpt / *.onnx / *.safetensors / *.bin` | 模型权重 | ❌ 已忽略 |
| `pipelines/*/models/` 下 HF 权重目录 | 模型权重 | ❌ 已忽略 |
| `data/`、`pipelines/*/data/` | 数据集 / 中间数据 / 预测 csv | ❌ 已忽略 |

训练完**把报告提交进仓库**：

```bash
git add data_model/pipelines/*/reports data_model/pipelines/*/models/feature_order.txt data_model/pipelines/*/models/manifest.txt
git commit -m "feat(model): 补 <line> 训练指标报告"
```

自查（可选）：

```bash
git check-ignore -v data_model/pipelines/expert/models/et_v1.pkl        # 应命中（被忽略）
git check-ignore -v data_model/pipelines/expert/reports/model_metrics.md # 应无输出（可提交）
```

## 7. 模型数据回传（另一台电脑训练完 → 传回本机）

模型权重不入库，训练完必须单独回传。先明确「传什么」：

| 类别 | 内容 | 体积 | 回传方式 |
|---|---|---|---|
| **必须传**：交付权重（`expert_models_20261024.zip`，包内平铺 10 个文件，不带目录层级） | 8 个 `.pkl` + `feature_order.txt` + `manifest.txt`，交付集仍是 `lr_v1` / `rf_v1` / `xgb_v1` | 10 个文件**未压缩合计 591,701,820 B（约 564MiB）**；其中 `et_v1.pkl` 572,936,009 B、`rf_v1.pkl` 收敛后 12,715,033 B（2026-10-24 前为 292,996,489 B） | **超飞书单文件 153MB 上限 → 走网盘（C）或分卷（B）**。包级体积与 MD5 须构建后实测回填（§7.2 / §7.4） |
| 可选：灌库用数据（`deliver_data_20261024.zip`） | `commits.csv` / `commit_features.csv` / `prediction_result.csv` | **18,006,911 B（约 17MB）** | 仅在对方不想自己跑 01–04+07 却要看真实列表时发；默认不发 |
| 其余评估权重（已含在上面的 10 文件包里，勿重复索取） | `et_v1` 572,936,009 B、`svm_v1` 3,385,933 B、`lgbm_v1` 1,028,836 B、`tabnet_v1` 300,437 B、`mlp_deep_v1` 95,809 B | 约 551MiB | 不再单独走网盘；只需收 `expert_models_20261024.zip` 一个包 |
| 报告 / 图表 / 清单 | `reports/*.md`、`figs/*.png`、`manifest.txt` | 小 | **走 git 提交** |

> **为什么交付三个而不是只交 `xgb_v1.pkl`**：`backend/app/model_registry.py::load_models()` 会
> `glob("*.pkl")` 加载 `MODEL_DIR`（默认 `data_model/pipelines/expert/models/`）下的**全部** `.pkl`；
> `POST /api/predict` 接受显式 `model_name`，未加载的名字直接返回 `40001 参数非法`。
> `feature_order.txt` 的 `[models]` 也列了 `lr_v1` / `rf_v1` / `xgb_v1` 三项。
> 只回传 `xgb_v1.pkl` 时，`lr_v1` / `rf_v1` 的请求会全部失败，与契约不一致。

### 7.1 训练机上先提交报告（走 git）

```bash
git add data_model/pipelines/*/reports data_model/pipelines/*/models/feature_order.txt data_model/pipelines/*/models/manifest.txt
git commit -m "feat(model): <line> 训练指标报告"
git push
```

### 7.2 打包模型（训练机上执行）

统一只产出一个包：**`expert_models_20261024.zip`**，包内**平铺 10 个文件**（8 个 `.pkl` + `feature_order.txt` + `manifest.txt`），不要带 `data_model/pipelines/expert/models/` 目录层级——否则收包方解压后路径对不上 §7.4 的校验命令。

打包前先按当前权重重新生成清单（`rf_v1` 收敛后 md5/体积已变，旧清单必然 `--check` 失败）：

```bash
cd data_model
python -m pipelines.verify_all_weights --write-manifest
python -m pipelines.verify_all_weights --check      # 期望：清单一致（8 项）
```

```powershell
# 训练机：仓库根目录执行
$m = "data_model/pipelines/expert/models"
$names = @("lr_v1.pkl","rf_v1.pkl","xgb_v1.pkl","et_v1.pkl","svm_v1.pkl","lgbm_v1.pkl","tabnet_v1.pkl","mlp_deep_v1.pkl","feature_order.txt","manifest.txt")
Compress-Archive -Path ($names | ForEach-Object { Join-Path $m $_ }) -DestinationPath expert_models_20261024.zip
```

```bash
# Linux：进到 models 目录后用 -j 压平，避免带目录层级
cd data_model/pipelines/expert/models
zip -j ../../../../expert_models_20261024.zip \
  lr_v1.pkl rf_v1.pkl xgb_v1.pkl et_v1.pkl svm_v1.pkl lgbm_v1.pkl tabnet_v1.pkl mlp_deep_v1.pkl \
  feature_order.txt manifest.txt
```

产出后立刻记录并回填本节的包级事实（当前仓库里没有该 zip，`data/` 与 `models/*.pkl` 都不入库，因此包级数值**在实测回填前一律视为待验收**）：

```powershell
Get-Item .\expert_models_20261024.zip | Select-Object Length
Get-FileHash .\expert_models_20261024.zip -Algorithm MD5, SHA256
```

### 7.3 选一种方式传回本机

| 方式 | 适用 | 说明 |
|---|---|---|
| **A. 飞书群聊「想到什么取什么」** | 小文件（约 20MB 内） | 在飞书把 zip 直接拖进群；或用 CLI：`lark-cli im +messages-send --chat-id oc_838d67f14658f59672782cd7e2166f69 --file ./<小包>.zip --as user` |
| **B. 分卷压缩** | 只在超 153MB 时用：当前 10 文件包（未压缩约 564MiB）就属于这种，`et_v1.pkl` 单文件已 546MiB | 分卷后逐卷发群 / 云盘，回传后合并：`7z a -v20m expert_models_20261024.7z expert_models_20261024/*`（每卷 20MB，先解压平铺再分卷），合并解压 `7z x expert_models_20261024.7z.001` |
| **C. 网盘** | 任意大小 | 上传百度网盘 / 阿里云盘，发分享链接 |
| **D. 局域网直传** | 同一局域网 | Windows 共享文件夹 / `scp` / `rsync` |

> ⚠️ 实测：飞书云盘 `drive +upload` 单文件 153MB 会报 `file size beyond limit`（错误码 1061043）。当前 `expert_models_20261024.zip` 的 10 个文件未压缩合计约 **564MiB**（`et_v1.pkl` 单文件 546MiB），**已超上限，不能直接发群（A）**，须走网盘（C）或分卷（B）。只有只含三模型的瘦包（`lr_v1` + `rf_v1` + `xgb_v1` + 两份清单，合计约 14MiB）才能用 A。

### 7.4 回传后校验与归位

```powershell
# 两端 MD5 / SHA256 一致即传输完整（与 §7.2 产出后记录的值对比）
Get-FileHash .\expert_models_20261024.zip -Algorithm MD5
Get-FileHash .\expert_models_20261024.zip -Algorithm SHA256
```

解压后**先跑清单校验**，这是收包方能独立复现的第一步（包内 `manifest.txt` 与实况必须逐项一致）：

```bash
cd data_model
python -m pipelines.verify_all_weights --check
# 期望（2026-10-24 本机实测，见下方记录）：
#   [verify] 清单一致（8 项）
#   [verify] 全部通过：8/8 可加载，特征宽度 [14]
#   退出码 0；不一致时退出码 2
```

解压 / 合并后，把 `.pkl` 放回 **`data_model/pipelines/expert/models/`**（`backend/app/config.py` 的 `MODEL_DIR` 默认指向这里，`load_models()` 加载该目录下全部 `*.pkl`），并逐个验证：

```bash
python -c "import joblib; [print(n, type(joblib.load('data_model/pipelines/expert/models/'+n+'.pkl')).__name__) for n in ('lr_v1','rf_v1','xgb_v1')]"
# 期望：lr_v1 Pipeline / rf_v1 RandomForestClassifier / xgb_v1 XGBClassifier
```

再确认后端确实把三个模型都注册进来（`MODEL_DIR` 无模型时返回空表，predict 只能给 50000）：

```bash
python -c "import sys; sys.path.insert(0,'backend'); from app import model_registry; model_registry.load_models(); print(sorted(model_registry._REGISTRY))"
# 期望至少含 ['lr_v1', 'rf_v1', 'xgb_v1']（外加目录里其他能正常回读的模型）
```

> 历史遗留：目录里若还有四包拆分前旧脚本产出的 `tabnet_v1.pkl`（类定义在 `__main__`），
> `joblib.load` 会 `AttributeError`；`load_models()` 按契约三只记日志并跳过，不影响其余模型。
> 用当前 `pipelines/expert/train.py` 重训即可覆盖成可回读的版本。

#### 7.4.1 实测记录（2026-10-24，本机 `data_model/pipelines/expert/models/`）

以下是在**未解压任何 zip、直接用工作区权重目录**跑出的原始输出，可当作 §7.4 的期望值基线；
包级 MD5/体积尚未实测（zip 不入库），两项仍为**待验收**，构建后回填到 §7.2/§7.4 的表里。

```
$ cd data_model && python -m pipelines.verify_all_weights --check
[verify] 线=expert 目录=.../data_model/pipelines/expert/models 共 8 个权重
et_v1.pkl       159f751f22bcad2ff11d53646e5cbc28   546.4MB  sklearn.ensemble._forest.ExtraTreesClassifier
lgbm_v1.pkl     5b34ddfb98cfc628cd17f1a2f4cf068e     1.0MB  lightgbm.sklearn.LGBMClassifier
lr_v1.pkl       28c65f8c3d653af53af71fac350f42fe     0.0MB  sklearn.pipeline.Pipeline
mlp_deep_v1.pkl 97447d2f1874e579410e8f23489e629d     0.1MB  sklearn.pipeline.Pipeline
rf_v1.pkl       ca80c58656263c13079aa65ca0112b47    12.1MB  sklearn.ensemble._forest.RandomForestClassifier
svm_v1.pkl      be0a7d26c72faabbd371c83710d84550     3.2MB  sklearn.pipeline.Pipeline
tabnet_v1.pkl   201a002b78c61a9589bec9b14496533c     0.3MB  sklearn.pipeline.Pipeline
xgb_v1.pkl      56138e2b4b55fbcae83aaa2866d244de     1.2MB  xgboost.sklearn.XGBClassifier
[verify] 清单一致（8 项）
[verify] 全部通过：8/8 可加载，特征宽度 [14]（6.9s）
退出码 0
```

```
$ cd backend && python -c "from app import model_registry; model_registry.load_models(); print(sorted(model_registry._REGISTRY))"
REGISTRY= ['lr_v1', 'rf_v1', 'xgb_v1']
```

> 两条结论的边界：`8/8` 只说明**评估可用**，在线可加载集仍是 `feature_order.txt` 的 `[models]` 三项（R6），
> 与 #134 的八模型在线切换提案无关——该提案尚未改变当前交付边界。
> 另：`manifest.txt` 已按收敛后的 `rf_v1`（`ca80c586…` / 12,715,033 B）重新生成；
> 旧清单里记的是收敛前的 `1960cd98…` / 292,996,489 B，任何拿旧清单对 `--check` 的做法都会得到退出码 2。

> 说明：`data/`（数据集与中间 CSV）不随 git 也不随回传包走；若换机后需要，按第 4 节整目录拷贝或重跑 01–05。

## 8. 常见问题

| 现象 | 处理 |
|---|---|
| `torch.cuda.is_available()` 为 False | 装成 CPU 版或驱动不匹配 → 重跑第 3 步 CUDA 安装 |
| e2e 显存不足（OOM） | `--batch-size 8`（累积步自动补有效 batch） |
| 首次跑 semantic/e2e 卡在下载 | 需联网下载 `microsoft/codebert-base`（~500MB）；离线机预缓存后设 `HF_HUB_OFFLINE=1` |
| 指标与别人不一致 | 只用 `data_model/environment.yml` 装环境，禁止再造 `requirements.txt` |
| fused 报覆盖率 < 99% 失败 | 先跑完 semantic 再跑 fused（缓存缺失） |
| `python` 打开应用商店 | conda 未激活 → 用 Anaconda Prompt 或 `conda init` |

## 9. 协作与交付备注

- **后端线复用同一环境**：`backend/` 不再有 `requirements.txt`，装环境同样用 `data_model/environment.yml`（需后端负责人周知）。
- **改动走 PR**：分支 `<类型>/<线>/<简述>`，禁止直推 `main`；合入后 `openspec archive <change-id>`。
- **历史证据不改写**：`backend/scripts/evidence/*`、`docs/common/test-report-sprint1.md` 保留当时状态。
- **已知遗留**：`check_links.py` 报的 11 个断链是四包拆分前的旧路径（`06_train_model.py`、计划中的 `10~16_*.py` 等），与环境配置无关，另行清理。

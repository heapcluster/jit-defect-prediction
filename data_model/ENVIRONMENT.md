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
**分类器数量**以各包 `config.py` 的 `DEFAULT_MODELS` 为准（expert 8 种；semantic 12 种）。

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
| 必需交付模型 | `xgb_v1.pkl`（后端唯一加载）+ `feature_order.txt` | 约 1.2MB | 飞书群聊 / 云盘直接发 |
| 全量评估模型 | 8 个 `.pkl`（`et_v1` 546MB、`rf_v1` 279MB 等） | 约 830MB | 分卷压缩 / 网盘 |
| 报告 / 图表 / 清单 | `reports/*.md`、`figs/*.png`、`manifest.txt` | 小 | **走 git 提交** |

### 7.1 训练机上先提交报告（走 git）

```bash
git add data_model/pipelines/*/reports data_model/pipelines/*/models/feature_order.txt data_model/pipelines/*/models/manifest.txt
git commit -m "feat(model): <line> 训练指标报告"
git push
```

### 7.2 打包模型（训练机上执行）

```powershell
# 只发交付模型（推荐，最小，后端够用）
Compress-Archive -Path data_model/pipelines/expert/models/xgb_v1.pkl,data_model/pipelines/expert/models/feature_order.txt -DestinationPath jit_delivery_xgb.zip

# 全量 8 模型（大，压缩后约 153MB）
Compress-Archive -Path data_model/pipelines/expert/models/* -DestinationPath expert_models.zip
```

```bash
# Linux
zip -r expert_models.zip data_model/pipelines/expert/models
```

### 7.3 选一种方式传回本机

| 方式 | 适用 | 说明 |
|---|---|---|
| **A. 飞书群聊「想到什么取什么」** | 小文件（约 20MB 内） | 在飞书把 zip 直接拖进群；或用 CLI：`lark-cli im +messages-send --chat-id oc_838d67f14658f59672782cd7e2166f69 --file ./jit_delivery_xgb.zip --as user` |
| **B. 分卷压缩** | 大文件（全量 830MB） | 分卷后逐卷发群 / 云盘，回传后合并：`7z a -v20m expert_models.7z data_model/pipelines/expert/models/*`（每卷 20MB），合并解压 `7z x expert_models.7z.001` |
| **C. 网盘** | 任意大小 | 上传百度网盘 / 阿里云盘，发分享链接 |
| **D. 局域网直传** | 同一局域网 | Windows 共享文件夹 / `scp` / `rsync` |

> ⚠️ 实测：飞书云盘 `drive +upload` 单文件 153MB 会报 `file size beyond limit`（错误码 1061043）。**大文件请用分卷（B）或网盘（C）**；小交付包（`jit_delivery_xgb.zip`）可直接发群（A）。

### 7.4 回传后校验与归位

```powershell
# 两端 SHA256 一致即传输完整
Get-FileHash .\jit_delivery_xgb.zip -Algorithm SHA256
```

解压 / 合并后，把 `.pkl` 放回 **`data_model/pipelines/<line>/models/`**（后端按此路径加载 `xgb_v1.pkl`），并验证：

```bash
python -c "import joblib; m=joblib.load('data_model/pipelines/expert/models/xgb_v1.pkl'); print(type(m))"
# 能打印出模型类型即加载成功
```

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

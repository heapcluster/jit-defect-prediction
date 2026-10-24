# environment Specification

## Purpose

统一四条线（expert / semantic / fused / e2e）的 Python 运行环境来源：`data_model/environment.yml` 是唯一权威清单，仓库内不再保留各自的 `requirements.txt`。

存在意义是「可复现」：同一份文件要能在 Windows（win-64）与 Linux/WSL、CPU 与 GPU 机器上建出依赖版本一致的环境，否则四条线的指标差异无法区分是模型差异还是环境差异。配套约束是 `data_model/ENVIRONMENT.md` 记录建环境、最小数据拷贝与国内网络镜像处理，任何人换机后按该文档可复现出同一环境。

## Requirements

### Requirement: 环境依赖单一权威文件

系统 SHALL 仅保留一份依赖清单 `data_model/environment.yml` 作为唯一权威环境文件；仓库根目录与各子目录 MUST NOT 再保留 `requirements.txt`。新增或升级依赖 MUST 只改此文件，并同步相关 README 的安装命令。

#### Scenario: 干净 clone 建环境

- **WHEN** 在干净 clone 后执行 `conda env create -f data_model/environment.yml`
- **THEN** 创建出 Python 3.12 环境 `jit-defect-prediction`，且包含模型四线与后端线所需依赖

#### Scenario: 禁止残留重复清单（边界）

- **WHEN** 审查仓库依赖文件
- **THEN** 除 `data_model/environment.yml` 外不存在任何 `requirements.txt`；若发现即为规格不一致缺陷

#### Scenario: 跨平台可移植（异常 / 边界）

- **WHEN** 在 Linux / WSL 或另一台 Windows 机器上创建环境
- **THEN** 环境文件不含写死 `prefix`、不含 win-64 专属 build，创建可完成

### Requirement: GPU 依赖安装可复现

系统 SHALL 在 `data_model/environment.yml` 文件头与相关 README 记录：RTX 4060 等 NVIDIA GPU 机器创建环境后，MUST 以 cu124 索引安装 `torch==2.5.1`，并可通过 `torch.cuda.is_available()` 验证。

#### Scenario: GPU 校验

- **WHEN** 在装有 NVIDIA 驱动的 4060 机器上按文档安装 CUDA 版 torch
- **THEN** `python -c "import torch; print(torch.cuda.is_available())"` 输出 `True`

# 设计决策（env-single-source）

## D1 唯一权威文件放 `data_model/` 而非仓库根

- **决策**：把 `environment.yml` 放到 `data_model/environment.yml`。
- **理由**：依赖主要服务模型线（torch / sklearn / xgboost 等），由模型线负责人维护；与「单环境 `jit-defect-prediction`」的既有计划一致。后端线复用同一环境，README 指向该文件即可。

## D2 删除全部 `requirements.txt` 而非保留副本

- **决策**：物理删除 6 个 `requirements.txt`。
- **理由**：多份清单必然漂移（本 change 起因就是 torch 版本冲突）。单一来源才能保证跨线指标可比。代价是需同步 20+ 处文档引用，由本 change 一次性完成。

## D3 版本以各线 `requirements.txt` 为准

- **决策**：`torch 2.5.1` / `transformers 4.46.1`（与 `semantic` / `e2e` 的 requirements 及 e2e README 的 CUDA 安装说明一致），而非旧 `environment.yml` 的 `2.14.1 / 5.19.0`。
- **理由**：e2e 微调与 semantic 编码以 4.46.1 生态验证；`torch 2.5.1 + cu124` 是项目既定的 4060 安装方式。旧根文件版本与各线不一致，属需修正的漂移。

## D4 不重写历史证据

- **决策**：`backend/scripts/evidence/coverage-2026-10-16.md`、`docs/common/test-report-sprint1.md` 中对 `backend/requirements.txt` 的引用保持原样。
- **理由**：它们记录变更发生时的真实状态，改写等于伪造证据。`check_links.py` 只校验 `data_model/` 前缀路径，不受影响。

## D5 跨平台

- **决策**：conda 段只留 `python` + `pip`，其余依赖走 pip，剔除 win-64 专属 build。
- **理由**：便于 Linux / WSL 或另一台 Windows 机器复现，避免环境创建在非本机失败。

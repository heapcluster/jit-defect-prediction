# 环境依赖收敛为单一权威文件（environment.yml 归位 data_model/）

> Sprint 2 ｜ 起草 2026-10-21 ｜ 起草人 蒋励（模型线负责人）
> 关联：`data_model/environment.yml`、各线 README、`docs/common/dev-handbook.md`

## Why

现状：仓库同时存在 1 个根目录 `environment.yml` + 6 个 `requirements.txt`（`backend/`、`data_model/`、4 个 pipeline），且版本各说各话——`environment.yml` 的 `torch 2.14.1 / transformers 5.19.0` 与各线 `requirements.txt` 的 `torch 2.5.1 / transformers 4.46.1` 直接冲突。换 RTX 4060 训练机时无法确定以哪个为准；且 `environment.yml` 写死本地 `prefix`、含 win-64 专属 build，跨机 / 跨平台不可复现。

## What Changes

1. `environment.yml` 迁移到 `data_model/environment.yml`（模型包根目录），作为**唯一权威**依赖文件；模型线与后端线共用同一 conda 环境 `jit-defect-prediction`。
2. 物理删除 6 个 `requirements.txt`：`backend/`、`data_model/`、`data_model/pipelines/{expert,semantic,fused,e2e}/`。
3. 版本对齐各线 `requirements.txt`：`torch==2.5.1`、`transformers==4.46.1`、`tokenizers==0.20.1`、`huggingface-hub==0.26.2`、`safetensors==0.4.5`；补 `accelerate==1.1.1`、`matplotlib==3.10.1`。
4. `environment.yml` 去 `prefix`、去 win-64 专属 build（跨平台）。
5. 同步更新所有活文档的安装命令与路径引用。

## 影响与边界

| 项 | 内容 |
|---|---|
| 影响目录 | `data_model/`（environment.yml 归位）、`backend/`（删 requirements.txt，读环境改指新文件）、`docs/`（安装命令）、`openspec/specs/`（路径引用） |
| 触及 `docs/design/sprint0-scope.md` 边界？ | **否**（不改变系统边界与功能） |
| **不做什么** | ① 不改变任何模型算法、接口字段、库表、时间序切分；② **不重写历史证据**（`backend/scripts/evidence/*`、`docs/common/test-report-sprint1.md` 记录当时真实状态，保持原样）；③ 不动 `openspec/changes/archive/`；④ 不新增功能与依赖（仅归并 + 对齐既有版本）。 |

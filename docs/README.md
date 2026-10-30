# docs/ — 规格与活文档

本目录放跨线规格、契约与各线的活文档（实现说明、验收、证据）。代码以 `api-spec.md` / `feature-columns.md` 等契约为唯一依据，改动走 OpenSpec change。

## 导航

- **`backend/`** — 后端与接口线（吕建江）
  - `README.md` — 线的职责、目录、启动、边界、非功能证据要求
  - `api-spec.md` — 八条接口 / 鉴权 / 错误码（契约三 v1.7 冻结）
  - `mysql-setup.md` — 演示库 `jit_demo` 的 MySQL 安装 / 一条命令建库 / `.env` 写法 / 验收清单（Issue #142，建库与特征口径的权威）
  - `acceptance.md` — 后端验收功能板块与「达到什么效果」
  - `implementation.md` / `openspec-compliance.md` — 架构与改动规范
- **`design/`** — 跨线设计（数据库、sprint0 范围等）
- **`model/`** — 数据与模型线（蒋励）：特征口径、数据管线、训练交付

## 约定

- 文档与代码不同步 = 缺陷：改接口 / 库表 / 特征必须先提 OpenSpec change，再同步对应 spec。
- 密钥、个人绝对路径不进文档（活文档只写给别人能复现的步骤）。

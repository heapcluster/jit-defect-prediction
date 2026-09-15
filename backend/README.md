# backend/ — 后端与接口线

**负责人**：吕建江

## 职责

建数据库表、预测接口、查询接口、结果解释模块、接口鉴权与输入校验。

## 交付物

接口实现、数据库表与 ER 图、鉴权与校验代码、OpenAPI（Swagger）接口文档。

## 边界

- 技术栈：Python + FastAPI + SQLAlchemy + MySQL 8。
- 接口格式以 `docs/` 下的契约文档为准；改契约必须走 OpenSpec change。
- 只在本目录内写代码。

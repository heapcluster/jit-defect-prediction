# 本机运行与联调入口

本页只记录可复用的启动顺序；接口、库表与页面细节分别见 `docs/api/`、`docs/database/`、`docs/web_page/`。个人密码、令牌和仓库绝对路径仅写本机未跟踪的 `.env`，不得写入 PR。

1. 在仓库根目录准备环境：`conda env create -f data_model/environment.yml`（已有环境可跳过创建），再执行 `conda activate jit-defect-prediction`。前端需符合 `frontend/package.json` 的 Node 版本要求。
2. 将 `backend/.env.example` 复制为 `backend/.env`，配置 MySQL `jit_demo` 的账号与密码；要同步实时提交时填写本机 `SOURCE_REPO`，其目录须含 `.git`。`MODEL_DIR` 留空时回落到仓库内 expert 权重目录，但权重本体需另行取得并核对，不在 Git 中。
3. 确保 MySQL 中已存在并授权 `jit_demo`；在 `backend/` 运行 `python -m app.db init` 建立现行五表，再运行 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。旧七表库不会被 `create_all` 自动迁移，应在隔离库重建并验证。
4. 将 `frontend/.env.example` 复制为 `frontend/.env.local`，确保 `VITE_API_KEY` 与后端 `API_TOKEN` 相同；在 `frontend/` 运行 `npm ci`、`npm run dev -- --host 127.0.0.1`，打开 `http://127.0.0.1:5173/`。
5. 先查公开的 `GET /api/health`，再带 `X-API-Key: <本机 API_TOKEN>` 查 `GET /api/models`；本地 Git 源可用时再从页面触发同步，或带同一请求头调用 `POST /api/sync`。该接口异步返回，随后轮询 `GET /api/sync/status`，确认 `running=false`、`last_error` 为空，再查询 `/api/commits`。无数据与同步失败要分开记录。

MySQL 建库授权、真实权重、浏览器截图及运行日志须由实际操作者在 PR 或飞书验收记录中留证；本页不宣称这些步骤已在当前机器通过。

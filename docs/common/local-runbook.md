# 本机运行说明

本机环境、建库、启动前后端和同步数据的当前步骤见仓库根目录的 [`README.md`](../../README.md#二本机开发不用容器)。该文件是运行命令的唯一正文；此处只提供旧 OpenSpec 引用所需的导航入口。

离线测试数据与实时同步结果应分别留证，不能互相冒充。真实数据库、权重和页面验收仍须由实际操作者执行并记录。

**本机代理提醒**：若终端或 `backend/.env` 配了 `HTTP_PROXY` / `HTTPS_PROXY`，必须同时设 `NO_PROXY=127.0.0.1,localhost`（`.env.example` 已给出），否则 `httpx` / `requests` 连本机 8000 也会走代理并报连接被拒。脚本侧可用 `httpx.Client(trust_env=False)` 兜底。

**同步离线提示**：`SYNC_FETCH=0` 时刷新跳过 `git fetch`，直接使用 `SOURCE_REPO` 的本地 HEAD，适合固定版本/断网演示；需要追踪远端新提交时保持默认 `1`。

**一句话风险总结**：`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 三项配置后由 LLM 生成（OpenAI 兼容 `/chat/completions`）；缺任一项或调用失败时自动回退模板句，不影响详情/预测。Key 只写本机 `.env`，不入库。

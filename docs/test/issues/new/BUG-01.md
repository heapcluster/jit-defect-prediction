# [缺陷][后端] 干净检出缺 `backend/static/` 目录，`app.main` 导入即失败，服务与全部后端测试无法启动

- 建议级别：**严重**
- 建议 label：`type:bug` `line:backend`
- 被测提交：`2734c1b`（main）
- 发现人：测试方（neon 线自动化执行，2026-11-15）

## 现象

在新克隆的仓库里，`uvicorn app.main:app` 启动和 `pytest` 收集都会直接失败：

```text
RuntimeError: Directory 'D:\...\jit-defect-prediction\backend\static' does not exist
```

`backend/app/main.py:101` 无条件执行 `app.mount("/static", StaticFiles(directory=...))`，而 `backend/static/` 本身不入版本控制（`.gitignore:59` 忽略了 `backend/static/figures/`，目录连同占位文件都没有）。

## 复现步骤

1. 前置：全新克隆 `git clone <repo>`，未做过任何构建；依赖按 `data_model/environment.yml` 装好；`backend/.env` 按 `.env.example` 配好。
2. 执行：
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   # 或
   python -m pytest -q
   ```
3. 频率：必现（100%），与机器和 Python 版本无关。

本地验证过的绕过方式（仅用于继续测试，不是修复）：`New-Item -ItemType Directory backend/static/figures`，建目录后两个命令立刻恢复正常。

## 预期结果

干净检出后，按 `README.md`「本机开发」执行 `uvicorn` 与 `pytest` 应能直接启动/收集，不需要人工先建目录。

## 实际结果

- `uvicorn` 启动即抛 `RuntimeError`，进程退出；
- `pytest` 报 collection error，254 条用例一条都收集不到；
- 建目录后：`pytest -q` → 254 passed，服务正常启动。

## 影响范围

- **环境**：任何新克隆 / CI 全新环境 / 容器以外的新机器，第一次跑就撞；老开发者本机因残留目录看不出问题。
- **功能**：静态图路由 `/static/**` 依赖该目录，目录缺失时服务根本无法 import，属启动级阻断。
- **测试**：后端单测、集成脚本、系统测试全部无法开始，阻塞四类测试。
- **验收影响**：阻断验收 A-17（按部署说明从零复现）。

## 建议修复方向（供 owner 参考，测试方不实施）

- 方案 A：`create_app()` 里在 mount 前加 `config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)`；
- 方案 B：提交 `backend/static/figures/.gitkeep` 并调整 `.gitignore` 只忽略 `*.png`；
- 两者取其一即可，判据：干净克隆后 `pytest -q` 与 `uvicorn` 直接可用。

## 证据

- 报错原文与复现记录：`docs/test/unit_test/unit_test_report.md` §2
- 缺陷台账：`docs/test/system_test/bug_list.md` BUG-01

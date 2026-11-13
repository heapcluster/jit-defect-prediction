"""三浏览器 / 逐接口页面走查：自动采集验收与联调截图，最大限度减少人工操作。

课程 §4.1 兼容性（Chrome / Edge / Firefox ≥3）、§3.3 前后端联调记录、
§5.3 验收逐条执行截图。本脚本把「逐页点开并截图」自动化，人只需运行一次并复核截图。

前置：
  - 前端 vite @ http://127.0.0.1:5173、后端 uvicorn @ http://127.0.0.1:8000 已启动；
  - API_TOKEN 可用（环境变量或 backend/.env）；
  - 安装 Playwright 浏览器（仅需在允许安装的环境执行一次）：
        pip install playwright
        playwright install chrome msedge firefox   # 或 playwright install chromium

运行：
  cd backend
  python scripts/browser_walkthrough.py --sha <最终提交SHA>
  python scripts/browser_walkthrough.py --browsers chrome,firefox --skip-linkage

输出：
  - 验收截图 -> docs/test/acceptance_test/execution_records/
  - 联调截图 -> docs/test/integration_test/screenshots/
  - 清单     -> 两个目录下的 walkthrough-manifest.json（含 SHA、浏览器、页面、文件、跳过原因）

注意：脚本**不启动服务、不伪造截图、不修改文档结论**；浏览器不可用时如实记为 skip。
截图仍需人工复核内容与脱敏后再用于交付。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
DEFAULT_ACCEPTANCE = REPO_DIR / "docs/test/acceptance_test/execution_records"
DEFAULT_LINKAGE = REPO_DIR / "docs/test/integration_test/screenshots"

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # 缺依赖时不伪造结果
    sync_playwright = None

BROWSERS = {
    "chrome": {"engine": "chromium", "channel": "chrome"},
    "msedge": {"engine": "chromium", "channel": "msedge"},
    "firefox": {"engine": "firefox", "channel": None},
}

# (用例编号, 关联接口, 路径模板, 文件名后缀, 是否同时作为联调截图)
PAGES = [
    ("A-01", "GET /api/commits", "/", "risk-list", True),
    ("A-05", "GET /api/trends", "/trend", "trend-board", True),
    ("A-06", "GET /api/figures", "/model-performance", "model-performance", True),
    ("A-08", "GET /api/commits/{hash} 40400", "/commit/" + "f" * 40, "commit-not-found", True),
    ("A-16", "兜底路由", "/this-route-does-not-exist", "not-found", False),
]


def current_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_DIR, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def detail_page(commit_hash: str):
    return ("A-10", "GET /api/commits/{hash}", f"/commit/{commit_hash}", "commit-detail", True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:5173"))
    ap.add_argument("--api-url", default=os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--token", default=os.getenv("API_TOKEN", ""))
    ap.add_argument("--sha", default=current_sha())
    ap.add_argument("--browsers", default="chrome,msedge,firefox")
    ap.add_argument("--commit-hash", default="")
    ap.add_argument("--acceptance-dir", type=Path, default=DEFAULT_ACCEPTANCE)
    ap.add_argument("--linkage-dir", type=Path, default=DEFAULT_LINKAGE)
    ap.add_argument("--skip-linkage", action="store_true")
    args = ap.parse_args()

    if sync_playwright is None:
        print("[walk] 缺少 playwright，未生成任何截图。请先在允许安装的环境执行：")
        print("[walk]   pip install playwright && playwright install chrome msedge firefox")
        return 2

    args.acceptance_dir.mkdir(parents=True, exist_ok=True)
    args.linkage_dir.mkdir(parents=True, exist_ok=True)

    commit_hash = args.commit_hash
    if not commit_hash and args.token:
        try:
            import urllib.request

            req = urllib.request.Request(
                f"{args.api_url}/api/commits?size=1",
                headers={"X-API-Key": args.token},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                items = json.load(resp)["data"]["items"]
            if items:
                commit_hash = items[0]["commit_hash"]
        except Exception as exc:  # noqa: BLE001
            print(f"[walk] 取 commit_hash 失败（{exc}），详情用例将跳过")

    pages = list(PAGES)
    if commit_hash:
        pages.append(detail_page(commit_hash))

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sha": args.sha,
        "base_url": args.base_url,
        "browsers_requested": args.browsers.split(","),
        "commit_hash": commit_hash or None,
        "results": [],
        "note": "脚本自动采集，截图内容须人工复核与脱敏；未执行的浏览器如实记为 skip。",
    }

    with sync_playwright() as p:
        for name in args.browsers.split(","):
            name = name.strip()
            if name not in BROWSERS:
                manifest["results"].append({"browser": name, "status": "unknown_browser"})
                continue
            cfg = BROWSERS[name]
            try:
                engine = getattr(p, cfg["engine"])
                kwargs = {"headless": True}
                if cfg["channel"]:
                    kwargs["channel"] = cfg["channel"]
                browser = engine.launch(**kwargs)
            except Exception as exc:  # noqa: BLE001
                print(f"[walk] {name} 启动失败，记为 skip：{exc}")
                manifest["results"].append({"browser": name, "status": "skip", "reason": str(exc)[:200]})
                continue

            try:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                if args.token:
                    context.set_extra_http_headers({"X-API-Key": args.token})
                page = context.new_page()
                for case_id, endpoint, path, slug, linkage in pages:
                    fname = f"{case_id}-{name}-{slug}.png"
                    try:
                        page.goto(args.base_url.rstrip("/") + path, wait_until="networkidle", timeout=30000)
                        page.wait_for_timeout(500)
                        page.screenshot(path=str(args.acceptance_dir / fname), full_page=True)
                        if linkage and not args.skip_linkage:
                            page.screenshot(path=str(args.linkage_dir / f"IN-{name}-{slug}.png"), full_page=True)
                        manifest["results"].append(
                            {"browser": name, "case": case_id, "endpoint": endpoint, "file": fname, "status": "ok"}
                        )
                        print(f"[walk] {name} {case_id} -> {fname}")
                    except Exception as exc:  # noqa: BLE001
                        manifest["results"].append(
                            {"browser": name, "case": case_id, "status": "skip", "reason": str(exc)[:200]}
                        )
                        print(f"[walk] {name} {case_id} 失败：{exc}")
                context.close()
            finally:
                browser.close()

    for target in (args.acceptance_dir, args.linkage_dir):
        (target / "walkthrough-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    ok = sum(1 for r in manifest["results"] if r.get("status") == "ok")
    skipped = sum(1 for r in manifest["results"] if r.get("status") == "skip")
    print(f"[walk] 完成：ok={ok} skip={skipped} sha={args.sha}")
    print("[walk] 截图须人工复核；未覆盖三浏览器时请在 B 清单中保留兼容性走查项。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""`scripts/demo_preflight.py` 的回归测试（Issue #138）。

钉住的是「不静默通过、不拿跳过当绿」这条硬性要求：六条判据任一条不满足都必须
① 打印实际值、② 进 rc=1。全绿路径也要钉住 —— 尤其是令牌与库口令**任何情况下都不回显**，
以及判据 6 的「(hash, model) 恒 1 行 + prediction 总行数不变」确实能抓到 upsert 插新行。

不起真服务：`start_service` / `wait_ready` / `httpx.Client` 三处用假实现注入
（假 `start_service` 往真日志句柄里写启动日志，好让 `parse_startup_log` 走真代码路径）；
库用 tmp_path 下的真 SQLite 文件，行数与高风险行都是真查。
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Commit, CommitFeature, Prediction

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "demo_preflight.py"
HASH = "a" * 40
TOKEN = "dev-token-20260918"
FEATURES = {
    "ns": 1.0986, "nd": 1.6094, "nf": 1.9459, "entropy": 1.42,
    "la": -4.2720, "ld": -5.2753, "lt": 7.1136,
    "fix": 1,
    "ndev": 1.3863, "age": 2.5257, "nuc": 0.2513,
    "exp": 5.7683, "rexp": 3.8114, "sexp": 2.8904,
}
GOOD_LOG = "INFO:backend.model_registry:loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']\n"
FAILED_LOG = ("INFO:backend.model_registry:loaded models: ['lr_v1', 'xgb_v1']\n"
              "ERROR:backend.model_registry:failed models: ['rf_v1']\n")


def _load_module():
    spec = importlib.util.spec_from_file_location("demo_preflight_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["demo_preflight_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_db(tmp_path: Path, scores: list[tuple[str, float, str]]) -> str:
    """建一个文件型 SQLite 库并按 (hash, risk_score, model_name) 灌 commit/feature/prediction。"""
    url = f"sqlite:///{(tmp_path / 'preflight.db').as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    for commit_hash, score, model in scores:
        session.add(Commit(commit_hash=commit_hash, repo_name="camel", author_name="jdoe",
                           committed_at=datetime(2026, 8, 3, 9, 0, 0), message="CAMEL-1 fix"))
        session.add(CommitFeature(commit_hash=commit_hash, committed_at=datetime(2026, 8, 3, 9, 0, 0),
                                  feature_version="v1", **FEATURES))
        session.add(Prediction(commit_hash=commit_hash, model_name=model, risk_score=score,
                               predicted_at=datetime(2026, 9, 1, 8, 0, 0), feature_version="v1"))
    session.commit()
    session.close()
    engine.dispose()
    return url


class FakeResp:
    def __init__(self, status: int, payload: dict):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict:
        return self._payload


class FakeClient:
    """契约三的四条路径一律 200/code=0；`predict_status` 可改成非 200 来造反例。"""

    def __init__(self, predict_status: int = 200, predict_code: int = 0):
        self._predict_status = predict_status
        self._predict_code = predict_code

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None, headers=None):
        if url.rstrip("/").endswith("/api/commits"):
            return FakeResp(200, {"code": 0, "message": "ok",
                                  "data": {"items": [{"commit_hash": HASH}], "total": 1}})
        if "/api/trends" in url:
            return FakeResp(200, {"code": 0, "message": "ok", "data": {"granularity": "week", "items": []}})
        return FakeResp(200, {"code": 0, "message": "ok",
                              "data": {"commit_hash": HASH, "features": FEATURES, "explanation": []}})

    def post(self, url, json=None, headers=None):
        return FakeResp(self._predict_status,
                        {"code": self._predict_code, "message": "ok",
                         "data": {"commit_hash": HASH, "model_name": (json or {}).get("model_name"),
                                  "risk_score": 0.9}})


class RaisingClient(FakeClient):
    """按调用注入网络异常：`fail_get=True` 让 GET 抛；`post_fail_at=n` 让第 n 次起的 POST 抛。"""

    def __init__(self, fail_get: bool = False, post_fail_at: int = 0):
        super().__init__()
        self._fail_get = fail_get
        self._post_fail_at = post_fail_at
        self._posts = 0

    def get(self, url, params=None, headers=None):
        if self._fail_get:
            raise httpx.ConnectError("连接被拒")
        return super().get(url, params, headers)

    def post(self, url, json=None, headers=None):
        self._posts += 1
        if self._post_fail_at and self._posts >= self._post_fail_at:
            raise httpx.ConnectError("连接被重置")
        return super().post(url, json, headers)


class FakeProc:
    def __init__(self, returncode=None):
        self._rc = returncode

    @property
    def returncode(self):
        return self._rc

    def poll(self):
        return self._rc

    def terminate(self):
        self._rc = 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self._rc = -9


def _wire(monkeypatch, mod, tmp_path, db_url, *, log_text=GOOD_LOG, ready=True,
          backend_token=TOKEN, frontend_token=TOKEN, write_frontend=True,
          client=None):
    """把服务、HTTP、两份 .env 都换成可控的假实现，返回本次运行的 argv 尾巴。"""
    monkeypatch.setattr(mod.config, "DATABASE_URL", db_url)
    monkeypatch.setattr(mod.config, "MODEL_DIR", tmp_path / "models")
    monkeypatch.setenv("API_TOKEN", backend_token)

    backend_env = tmp_path / "backend.env"
    backend_env.write_text(f"# 注释行\nAPI_TOKEN={backend_token}\nDATABASE_URL={db_url}\n", encoding="utf-8")
    frontend_env = tmp_path / "frontend.env.local"
    if write_frontend:
        frontend_env.write_text(f'VITE_API_KEY="{frontend_token}"\n', encoding="utf-8")

    def fake_start(host, port, log_handle, env):
        log_handle.write(log_text.encode("utf-8"))
        log_handle.flush()
        return FakeProc()

    monkeypatch.setattr(mod, "start_service", fake_start)
    monkeypatch.setattr(mod, "wait_ready",
                        lambda c, base, proc, timeout: (ready, "HTTP 401（无令牌，401 即为已就绪）"
                                                        if ready else "120s 内未就绪，最后一次异常 ConnectError"))
    monkeypatch.setattr(mod.httpx, "Client", lambda **kw: client or FakeClient())
    return ["--backend-env", str(backend_env), "--frontend-env", str(frontend_env),
            "--port", "8099", "--timeout", "1"]


def _run(monkeypatch, mod, tmp_path, argv_extra, **wire_kwargs):
    db_url = wire_kwargs.pop("db_url")
    extra = _wire(monkeypatch, mod, tmp_path, db_url, **wire_kwargs)
    monkeypatch.setattr(sys, "argv", ["demo_preflight", *extra, *argv_extra])
    return mod.main()


# ── 纯函数 ──────────────────────────────────────────────────────────

def test_parse_dotenv_handles_quotes_comments_and_export(tmp_path):
    mod = _load_module()
    path = tmp_path / ".env"
    path.write_text('# 注释\n\nAPI_TOKEN="quoted-token"\nVITE_API_KEY=\'single\'\n'
                    "export MODEL_DIR=/tmp/x\r\nEMPTY=\r\nno_equals_line\r\n", encoding="utf-8")
    values = mod.parse_dotenv(path)
    assert values["API_TOKEN"] == "quoted-token"
    assert values["VITE_API_KEY"] == "single"
    assert values["MODEL_DIR"] == "/tmp/x"
    assert values["EMPTY"] == ""
    assert "no_equals_line" not in values


def test_mask_secret_and_database_url_never_leak():
    mod = _load_module()
    masked = mod.mask_secret("mysql-super-secret-token")
    assert "mysql-super-secret-token" not in masked and "secret" not in masked
    assert "24 字符" in masked
    assert mod.mask_secret("") == "***（空）"
    url = mod.mask_database_url("mysql+pymysql://jit:p@ssw0rd@127.0.0.1:3306/jit_demo")
    assert "p@ssw0rd" not in url and "jit_demo" in url and "***" in url
    assert mod.mask_database_url("sqlite:///./demo.db") == "sqlite:///./demo.db"
    assert mod.mask_database_url("") == "（空）"


def test_display_path_hides_paths_outside_repo(tmp_path):
    mod = _load_module()
    assert mod.display_path(tmp_path) == "<仓库外路径>"
    assert mod.display_path(mod.BACKEND_DIR / "scripts") == "backend/scripts"
    assert mod.display_path(None) == "（未设置）"


def test_parse_startup_log_reads_loaded_and_failed_lines():
    mod = _load_module()
    loaded, failed, raw = mod.parse_startup_log(GOOD_LOG)
    assert loaded == ["lr_v1", "rf_v1", "xgb_v1"] and failed is False and "loaded models" in raw
    loaded, failed, raw = mod.parse_startup_log(FAILED_LOG)
    assert loaded == ["lr_v1", "xgb_v1"] and failed is True and "failed models" in raw
    assert mod.parse_startup_log("什么都没有\n") == (None, False, "（启动日志里没有模型加载行）")


# ── 全绿路径 ────────────────────────────────────────────────────────

def test_all_six_pass_returns_0_and_masks_secrets(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    out = tmp_path / "evidence" / "preflight.md"
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1", "--out", str(out)], db_url=db_url)
    text = capsys.readouterr().out
    assert rc == 0, text
    for name in ("1 令牌一致", "2 库行数", "3 存在高风险行", "4 交付模型全部加载",
                 "5 四接口 200", "6 同 hash 两次预测只留一行"):
        assert f"PASS {name} ::" in text, name
    assert "汇总：6/6 通过" in text
    assert TOKEN not in text and TOKEN not in out.read_text(encoding="utf-8"), "令牌不得回显"
    evidence = out.read_text(encoding="utf-8")
    assert evidence.count("| PASS |") == 6 and "存在 FAIL" not in evidence
    assert "prediction 总行数 1 → 1" in text


# ── 判据 1：令牌 ────────────────────────────────────────────────────

def test_token_mismatch_fails_rc1_and_masks_both(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    out = tmp_path / "evidence" / "preflight-fail.md"
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1", "--out", str(out)],
              db_url=db_url, frontend_token="another-token-999")
    text = capsys.readouterr().out
    assert rc == 1, "令牌不一致必须进 rc"
    assert "FAIL 1 令牌一致 ::" in text and "不相等" in text
    assert "another-token-999" not in text and TOKEN not in text
    evidence = out.read_text(encoding="utf-8")
    assert "| FAIL |" in evidence and "存在 FAIL —— 别上台，也不得作为证据提交" in evidence
    assert "another-token-999" not in evidence and TOKEN not in evidence, "证据文件里也不许出现令牌"


def test_missing_frontend_env_fails_rc1(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1"],
              db_url=db_url, write_frontend=False)
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 1 令牌一致 ::" in text and "配置文件不存在" in text and "40100" in text


def test_empty_backend_token_fails_rc1(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    monkeypatch.delenv("API_TOKEN", raising=False)
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1"],
              db_url=db_url, backend_token="", frontend_token="")
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 1 令牌一致 ::" in text and "没有 API_TOKEN" in text
    assert "FAIL 4 交付模型全部加载 ::" in text and "不起服务" in text, "缺令牌不许 skip 成绿"


# ── 判据 2、3：库 ───────────────────────────────────────────────────

def test_empty_db_fails_2_3_and_blocks_456(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [])
    rc = _run(monkeypatch, mod, tmp_path, [], db_url=db_url)
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 2 库行数 :: prediction=0（期望 83943）" in text
    assert "FAIL 3 存在高风险行 ::" in text and "= 0" in text
    assert "FAIL 6 同 hash 两次预测只留一行 :: 前置不满足，未执行" in text


def test_seed_like_db_is_flagged_as_wrong_library(monkeypatch, tmp_path, capsys):
    """联调库形态（3 行 0.1/0.2/0.3）必须被判据 3 拦下，并明说「拿错库上台」。"""
    mod = _load_module()
    db_url = _make_db(tmp_path, [("0" * 39 + str(i), 0.1 * i, "seed_v1") for i in (1, 2, 3)])
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "3"], db_url=db_url)
    text = capsys.readouterr().out
    assert rc == 1
    assert "PASS 2 库行数 ::" in text
    assert "FAIL 3 存在高风险行 ::" in text and "拿错库上台" in text and "jit_demo" in text


def test_missing_database_url_fails_2_3(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    monkeypatch.setattr(mod.config, "DATABASE_URL", "")
    backend_env = tmp_path / "backend.env"
    backend_env.write_text(f"API_TOKEN={TOKEN}\n", encoding="utf-8")
    frontend_env = tmp_path / "frontend.env.local"
    frontend_env.write_text(f"VITE_API_KEY={TOKEN}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["demo_preflight", "--backend-env", str(backend_env),
                                      "--frontend-env", str(frontend_env), "--port", "8099"])
    rc = mod.main()
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 2 库行数 :: DATABASE_URL 未设置" in text


def test_unreachable_db_fails_with_driver_error(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    rc = _run(monkeypatch, mod, tmp_path, [], db_url=f"sqlite:///{(tmp_path / 'nope').as_posix()}/x.db")
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 2 库行数 :: 数据库不可用" in text


# ── 判据 4、5、6：服务 ──────────────────────────────────────────────

def test_failed_models_line_fails_check4(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1"],
              db_url=db_url, log_text=FAILED_LOG)
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 4 交付模型全部加载 ::" in text and "failed models" in text
    assert "PASS 5 四接口 200 ::" in text, "判据 4 挂了不该连累判据 5 的实测"


def test_service_not_ready_fails_456_with_log_tail(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1"],
              db_url=db_url, ready=False, log_text="boom: 端口被占用\n")
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 4 交付模型全部加载 :: 服务没起来" in text
    assert "FAIL 5 四接口 200 :: 服务未就绪，未执行" in text
    assert "FAIL 6 同 hash 两次预测只留一行 :: 服务未就绪，未执行" in text


def test_wait_ready_reports_early_exit_and_timeout():
    """真跑 wait_ready：进程先死 → 报退出码；一直连不上 → 报超时，两者都不许当成「就绪」。"""
    mod = _load_module()
    ok, detail = mod.wait_ready(FakeClient(), "http://127.0.0.1:1", FakeProc(returncode=3), 5)
    assert ok is False and "提前退出" in detail and "退出码 3" in detail
    ok, detail = mod.wait_ready(FakeClient(), "http://127.0.0.1:1", FakeProc(), 1)
    assert ok is True and "HTTP 200" in detail, "FakeClient 会应答，这条路应判就绪并回报状态码"
    ok, detail = mod.wait_ready(RaisingClient(fail_get=True), "http://127.0.0.1:1", FakeProc(), 1)
    assert ok is False and "未就绪" in detail and "ConnectError" in detail


def test_network_error_in_checks_fails_5_and_6(monkeypatch, tmp_path, capsys):
    """请求抛网络异常时不许静默通过：判据 5、6 都得 FAIL 且进 rc。"""
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1"],
              db_url=db_url, client=RaisingClient(fail_get=True))
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 5 四接口 200 :: 请求异常：ConnectError" in text
    assert "FAIL 6 同 hash 两次预测只留一行 :: 判据 5 的请求没跑完" in text


def test_network_error_on_second_post_fails_6(monkeypatch, tmp_path, capsys):
    """第一次 POST 成功、第二次断连：判据 5 过、判据 6 必须 FAIL（不许拿第一次当幂等证据）。"""
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1"],
              db_url=db_url, client=RaisingClient(post_fail_at=2))
    text = capsys.readouterr().out
    assert rc == 1
    assert "PASS 5 四接口 200 ::" in text
    assert "FAIL 6 同 hash 两次预测只留一行 :: 第二次 POST 异常：ConnectError" in text


def test_predict_500_fails_check5(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1"], db_url=db_url,
              client=FakeClient(predict_status=500, predict_code=50000))
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 5 四接口 200 ::" in text and "POST /api/predict → HTTP 500 code=50000" in text
    assert "契约三只有这四条路径" in text


def test_upsert_inserting_second_row_fails_check6(monkeypatch, tmp_path, capsys):
    """(hash, model) 从 1 行变 2 行 = 幂等被破坏，必须 FAIL。"""
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    calls = {"n": 0}
    real_count_pair = mod.count_pair

    def fake_count_pair(url, commit_hash, model_name):
        calls["n"] += 1
        return real_count_pair(url, commit_hash, model_name) if calls["n"] == 1 else 2

    extra = _wire(monkeypatch, mod, tmp_path, db_url)
    monkeypatch.setattr(mod, "count_pair", fake_count_pair)
    monkeypatch.setattr(sys, "argv", ["demo_preflight", *extra, "--expect-predictions", "1"])
    rc = mod.main()
    text = capsys.readouterr().out
    assert rc == 1
    assert "FAIL 6 同 hash 两次预测只留一行 ::" in text and "行数 1 → 2" in text


# ── CLI 守卫 ────────────────────────────────────────────────────────

def test_module_entry_prints_usage_flags():
    """`python -m scripts.demo_preflight --help` 真走一遍模块导入（含 app.config）。"""
    backend = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONUTF8="1")
    env.pop("PYTHONPATH", None)
    proc = subprocess.run([sys.executable, "-m", "scripts.demo_preflight", "--help"],
                          cwd=str(backend), env=env, capture_output=True, text=True, timeout=180, check=False)
    assert proc.returncode == 0, proc.stderr
    assert "--expect-predictions" in proc.stdout and "--frontend-env" in proc.stdout


def test_script_has_no_personal_paths():
    """入库文件不得含个人绝对路径（collaboration §0 第 3 条）。

    只查**真的**个人路径特征（盘符 + 用户目录、POSIX 家目录、本机用户名），
    不用裸 `[A-Za-z]:\\\\` —— 那会把脚本里合法的正则转义（如 `models:\\s*`）误判成路径。
    """
    body = SCRIPT.read_text(encoding="utf-8")
    for pattern in (r"[A-Za-z]:[\\/]+Users", r"[A-Za-z]:[\\/]+TeamWork", r"/Users/", r"/home/"):
        assert not re.search(pattern, body), f"命中个人路径特征 {pattern}"
    assert Path.home().name not in body, "入库文件里出现了本机用户名"


def test_evidence_file_never_contains_local_absolute_paths(monkeypatch, tmp_path, capsys):
    """`--out` 写出的证据文件是要入库的：本机绝对路径必须被换掉（collaboration §0 第 3 条）。

    这条是实跑抓到的真缺陷：SQLite 的 `DATABASE_URL` 本身就是 `sqlite:///` + 本机绝对路径，
    信息行原样写进证据文件等于把个人路径提交进仓库。
    """
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "xgb_v1")])
    out = tmp_path / "evidence" / "preflight.md"
    rc = _run(monkeypatch, mod, tmp_path, ["--expect-predictions", "1", "--out", str(out)], db_url=db_url)
    assert rc == 0
    evidence = out.read_text(encoding="utf-8")
    drive = str(tmp_path)[:2]
    for chunk in (str(tmp_path), str(tmp_path).replace("\\", "/"), drive + "\\Users", drive + "/Users"):
        assert chunk not in evidence, f"证据文件里出现了本机路径：{chunk}"
    assert "<本机路径>" in evidence, "应替换为占位符而不是直接删掉整行"

    sample = f"库：sqlite:///{(tmp_path / 'demo.db').as_posix()}；模型目录 {tmp_path / 'm'}；口令 ***"
    cleaned = mod.sanitize_for_evidence(sample, mod.local_replacements(f"sqlite:///{(tmp_path / 'demo.db').as_posix()}"))
    assert str(tmp_path) not in cleaned and "<本机路径>" in cleaned and "口令 ***" in cleaned


def test_sanitize_keeps_api_paths_and_repo_relative_paths():
    """兜底正则不许误伤：契约三的 `/api/...` 与仓库内相对路径必须原样留下。"""
    mod = _load_module()
    text = ("GET /api/commits → HTTP 200；GET /api/trends；POST /api/predict；"
            "pipelines/e2e/data/prediction_result.csv；backend/scripts/demo_preflight.py")
    assert mod.sanitize_for_evidence(text, {}) == text
    assert mod.sanitize_for_evidence("日志在 /tmp/x/uvicorn.log", {}) == "日志在 <本机路径>"
    assert mod.sanitize_for_evidence("库 sqlite:////tmp/pytest-x/db.sqlite", {}) == "库 sqlite:///<本机路径>"


@pytest.mark.parametrize("model_name", ["xgb_v1", "seed_v1"])
def test_pick_target_prefers_expected_models(tmp_path, model_name):
    mod = _load_module()
    db_url = _make_db(tmp_path, [(HASH, 0.9, "seed_v1"), ("b" * 40, 0.8, "xgb_v1")])
    picked = mod.pick_target(db_url, [model_name])
    assert picked is not None
    assert picked[1] == model_name

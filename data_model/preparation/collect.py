"""Independent W3.1 Git collector. No database, job store or user checkout writes."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import ipaddress
import json
import math
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit
from uuid import uuid4

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
MAX_REPO_BYTES = 2 * 1024**3
MAX_ROWS = 100000
MAX_COMMAND_BYTES = 512 * 1024**2


def _kill_process_group(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
    else:
        os.killpg(pid, signal.SIGKILL)
GIT_TIMEOUT = 180
CACHE_VERSION = "collect-json-v1"
SZZ_VERSION = "d4-backtracking-nullable-v1"
PHASES = ("validate", "repository", "commits", "szz", "features", "split")
FIELDS = {"repo_source", "branch", "dataset_name", "start_time", "end_time", "start_commit",
          "end_commit", "mode", "fetch_remote", "head_expect", "dedup", "szz_method", "split_ratio", "format"}
DEFAULTS = {"branch": None, "start_time": None, "end_time": None, "start_commit": None,
            "end_commit": None, "mode": "incremental", "fetch_remote": True, "head_expect": None,
            "dedup": "commit_hash", "szz_method": "szz_v1", "split_ratio": 0.7, "format": "csv"}


class CollectError(ValueError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _invalid(message: str):
    raise CollectError(40001, message)


def _json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _iso(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)", value):
        _invalid("时间须为带时区的 ISO 8601 datetime")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")
    except ValueError as exc:
        raise CollectError(40001, "时间非法") from exc


def _epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _hash(value, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        _invalid(f"{field} 须为 40 位十六进制提交哈希")
    return value.lower()


def _roots(allow_roots: list[str]) -> list[Path]:
    if not isinstance(allow_roots, list) or not allow_roots:
        _invalid("至少配置一个允许根目录")
    roots = []
    for raw in allow_roots:
        if not isinstance(raw, str) or not Path(raw).is_absolute():
            _invalid("允许根目录须为绝对路径")
        try:
            root = Path(raw).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise CollectError(40001, "允许根目录不存在") from exc
        if not root.is_dir():
            _invalid("允许根目录不是目录")
        roots.append(root)
    return roots


def _within(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo):
        return False
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def _url(source: str, protocols: list[str]) -> tuple[str, list[str]]:
    try:
        parsed = urlsplit(source)
        port = parsed.port or (443 if parsed.scheme == "https" else 9418)
    except ValueError as exc:
        raise CollectError(40001, "仓库 URL 非法") from exc
    host = parsed.hostname
    if (parsed.scheme not in protocols or parsed.scheme not in ("https", "git") or not host
            or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
            or not parsed.path or "\\" in source or any(ord(c) <= 32 for c in unquote(source))):
        _invalid("仓库 URL 协议、凭证或路径非法")
    host = host.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "%" in host:
        _invalid("拒绝本机或私有网络目标")
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host) or "." not in host:
            _invalid("网络主机名非法")
        try:
            addresses = sorted({entry[4][0] for entry in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
        except OSError as exc:
            raise CollectError(40001, "网络目标无法解析") from exc
    if not addresses or not all(_public_ip(address) for address in addresses):
        _invalid("拒绝本机、私有或保留网络目标")
    # Pin the validated addresses. HTTPS keeps hostname/TLS validation; git://
    # uses a validated numeric destination and never re-resolves an untrusted host.
    authority = f"[{host}]" if ":" in host else host
    if parsed.port:
        authority += f":{port}"
    canonical = urlunsplit((parsed.scheme, authority, parsed.path, "", ""))
    if parsed.scheme == "git":
        address = addresses[0]
        authority = f"[{address}]" if ":" in address else address
        canonical = urlunsplit(("git", f"{authority}:{port}", parsed.path, "", ""))
        return canonical, []
    return canonical, [f"http.curloptResolve={host}:{port}:{','.join('[' + a + ']' if ':' in a else a for a in addresses)}"]


def validate_config(raw: dict, *, allow_roots: list[str], protocol_whitelist: list[str]) -> dict:
    """Strict API-table validation. Resolve dataset_id in the caller, then remove it."""
    roots = _roots(allow_roots)
    if not isinstance(protocol_whitelist, list) or any(p not in ("https", "git") for p in protocol_whitelist):
        _invalid("协议白名单仅支持 https/git")
    if not isinstance(raw, dict) or set(raw) - FIELDS:
        _invalid("collect 配置包含未知字段")
    result = {**DEFAULTS, **raw}
    for key in ("repo_source", "dataset_name"):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > (4096 if key == "repo_source" else 255):
            _invalid(f"{key} 必填且须为非空字符串")
        if any(ord(c) < 32 for c in value):
            _invalid(f"{key} 含控制字符")
    if type(result["fetch_remote"]) is not bool:
        _invalid("fetch_remote 须为 bool")
    for key, choices in (("mode", ("full", "incremental")), ("dedup", ("commit_hash",)),
                         ("szz_method", ("szz_v1", "szz_lite")), ("format", ("csv", "xlsx"))):
        if not isinstance(result[key], str) or result[key] not in choices:
            _invalid(f"{key} 非法")
    ratio = result["split_ratio"]
    if type(ratio) not in (int, float) or not 0 < ratio < 1 or not math.isfinite(ratio):
        _invalid("split_ratio 须为 (0,1) 内的有限数值")
    result["split_ratio"] = float(ratio)
    branch = result["branch"]
    if branch is not None:
        if (not isinstance(branch, str) or not branch or len(branch) > 255
                or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", branch)
                or any(part.startswith((".", "-")) or part.endswith((".", ".lock")) or not part
                       for part in branch.split("/")) or ".." in branch or "//" in branch):
            _invalid("branch 须为安全 Git ref 或提交哈希")
    for key in ("start_commit", "end_commit", "head_expect"):
        if result[key] is not None:
            result[key] = _hash(result[key], key)
    for key in ("start_time", "end_time"):
        if result[key] is not None:
            result[key] = _iso(result[key])
    if result["start_time"] and result["end_time"] and _epoch(result["start_time"]) > _epoch(result["end_time"]):
        _invalid("start_time 晚于 end_time")
    source = result["repo_source"]
    if "://" in source:
        _url(source, protocol_whitelist)
    else:
        if "::" in source or not Path(source).is_absolute():
            _invalid("仓库须为绝对本地路径或 https/git URL")
        try:
            path = Path(source).resolve()
        except (OSError, RuntimeError) as exc:
            raise CollectError(40001, "仓库路径非法") from exc
        if not _within(path, roots):
            _invalid("仓库路径越过允许根目录")
        if not path.is_dir():
            raise CollectError(40400, "仓库不存在")
        result["repo_source"] = str(path)
    return result


class GitRunner:
    """argv-only Git, bounded timeout/output, no hooks/config helpers/prompts.

    progress is a zero-argument cancellation checkpoint. It is deliberately
    invoked outside exception conversion and its exceptions are never swallowed.
    """
    def __init__(self, protocols: list[str], progress, *, size_directory: Path | None = None):
        self.protocols = protocols
        self.progress = progress
        self.size_directory = size_directory
        self.network_config: list[str] = []

    def __call__(self, repo_dir: Path, *args: str, input_bytes: bytes | None = None,
                 binary: bool = False, allowed_exit_codes=(0,)):
        if self.progress:
            self.progress()
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("GIT_") and k.lower() not in ("http_proxy", "https_proxy", "all_proxy", "no_proxy")}
        env.update(GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                   GIT_LITERAL_PATHSPECS="1", GIT_ALLOW_PROTOCOL=":".join(self.protocols), LC_ALL="C")
        settings = ["core.hooksPath=" + os.devnull, "core.fsmonitor=false", "core.quotepath=false",
                    "core.pager=cat", "core.attributesFile=" + os.devnull, "credential.helper=",
                    "credential.interactive=false", "protocol.allow=never", "http.proxy=",
                    "http.followRedirects=false", "http.sslVerify=true", "http.schannelCheckRevoke=false",
                    "fetch.recurseSubmodules=false",
                    "submodule.recurse=false", "maintenance.auto=false", "gc.auto=0",
                    "diff.external=", "diff.trustExitCode=false"]
        settings.extend(f"protocol.{p}.allow=always" for p in self.protocols)
        # 与后端 services/git.py 同口径：代理只认显式注入的 GIT_PROXY（其次 HTTPS_PROXY）。
        # 校验后的仓库 URL 与协议白名单不变，仅本机出口走代理。
        proxy = os.getenv("GIT_PROXY", "").strip() or os.getenv("HTTPS_PROXY", "").strip()
        if proxy:
            settings = [item for item in settings if not item.startswith("http.proxy=")]
            settings.extend((f"http.proxy={proxy}", f"https.proxy={proxy}"))
            # 代理自己解析 DNS，不再 pin 直连 IP（否则绕过代理）。
            settings = [item for item in settings
                        if not item.startswith("http.curloptResolve=")]
            # MITM 代理的证书不被系统信任时，必须显式 opt-in 才放宽校验；默认强校验。
            if os.getenv("GIT_PROXY_INSECURE_TLS", "").strip() in ("1", "true", "TRUE"):
                settings = [item for item in settings if item != "http.sslVerify=true"]
                settings.append("http.sslVerify=false")
        settings.extend(self.network_config if not proxy else [])
        argv = ["git", "--no-pager"]
        for setting in settings:
            argv.extend(("-c", setting))
        argv.extend(("-C", str(repo_dir)))
        if args and args[0] in ("log", "show", "diff"):
            argv.extend((args[0], "--no-ext-diff", "--no-textconv", *args[1:]))
        elif args and args[0] == "blame":
            argv.extend((args[0], "--no-textconv", *args[1:]))
        else:
            argv.extend(args)
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err, tempfile.TemporaryFile() as stdin:
            if input_bytes is not None:
                stdin.write(input_bytes)
                stdin.seek(0)
            try:
                process = subprocess.Popen(argv, stdin=stdin, stdout=out, stderr=err, env=env,
                                           start_new_session=True)
            except OSError as exc:
                raise CollectError(50000, "无法启动 Git") from exc
            start = time.monotonic()
            try:
                while True:
                    if self.progress:
                        self.progress()
                    if out.tell() > MAX_COMMAND_BYTES or err.tell() > MAX_COMMAND_BYTES:
                        _invalid("Git 输出大小超限")
                    if self.size_directory and self.size_directory.exists():
                        _check_size(self.size_directory, self.progress, volatile=True)
                    remaining = GIT_TIMEOUT - (time.monotonic() - start)
                    if remaining <= 0:
                        raise CollectError(50000, "Git 命令超时")
                    try:
                        process.wait(timeout=min(0.1, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if self.progress:
                    self.progress()
                if process.returncode not in allowed_exit_codes:
                    # No argv/stderr in public errors: remote messages may contain secrets.
                    raise CollectError(50000, f"Git {args[0] if args else 'command'} 运行失败")
                if out.tell() > MAX_COMMAND_BYTES:
                    _invalid("Git 输出大小超限")
                out.seek(0)
                content = out.read()
                return content if binary else content.decode("utf-8", "replace")
            finally:
                if process.poll() is None:
                    try:
                        _kill_process_group(process.pid)
                    except ProcessLookupError:
                        pass
                    process.wait()

    def blob_line_counts(self, repo_dir: Path, specs: list[str], *, progress=None) -> dict[str, int]:
        result = {}
        for offset in range(0, len(specs), 128):
            if progress:
                progress()
            batch = specs[offset:offset + 128]
            if any("\n" in spec or "\r" in spec or "\x00" in spec for spec in batch):
                _invalid("Git 文件路径包含不支持的控制字符")
            output = self(repo_dir, "cat-file", "--batch", input_bytes=("\n".join(batch) + "\n").encode(), binary=True)
            position = 0
            for spec in batch:
                end = output.find(b"\n", position)
                if end < 0:
                    raise CollectError(50000, "Git cat-file 返回不完整")
                header = output[position:end].split()
                position = end + 1
                if header[-1:] == [b"missing"]:
                    result[spec] = 0
                    continue
                if len(header) != 3 or header[1] != b"blob":
                    raise CollectError(50000, "Git cat-file 对象格式非法")
                size = int(header[-1])
                body = output[position:position + size]
                if len(body) != size or output[position + size:position + size + 1] != b"\n":
                    raise CollectError(50000, "Git blob 返回不完整")
                position += size + 1
                result[spec] = body.count(b"\n") + int(bool(body) and not body.endswith(b"\n"))
        return result


def _check_size(directory: Path, progress=None, *, volatile: bool = False):
    total = 0
    for parent, directories, files in os.walk(directory, followlinks=False):
        if progress:
            progress()
        for name in directories + files:
            path = Path(parent) / name
            if path.is_symlink():
                _invalid("Git 存储不允许符号链接")
        for name in files:
            try:
                total += (Path(parent) / name).stat().st_size
            except FileNotFoundError:
                if not volatile:
                    raise
                # Git atomically renames temporary packs/refs while cloning.
                # A second non-volatile check follows successful completion.
                continue
            if total > MAX_REPO_BYTES:
                _invalid("仓库大小超限")


def _repository(path: Path, roots: list[Path], runner: GitRunner):
    if not (path / ".git").exists() and not ((path / "HEAD").is_file() and (path / "objects").is_dir()):
        raise CollectError(40400, "不是 Git 仓库")
    git_dir = Path(runner(path, "rev-parse", "--absolute-git-dir").strip()).resolve(strict=True)
    if not _within(git_dir, roots):
        _invalid("Git 存储路径越过允许根目录")
    _check_size(git_dir, runner.progress)
    common = Path(runner(path, "rev-parse", "--git-common-dir").strip())
    common = (path / common).resolve() if not common.is_absolute() else common.resolve()
    if not _within(common, roots):
        _invalid("Git 公共存储路径越界")
    _check_size(common, runner.progress)
    if (common / "objects/info/alternates").exists():
        _invalid("收集需要独立的仓库历史，不支持 alternates")
    if (common / "shallow").exists():
        _invalid("收集需要完整独立历史，不支持 shallow 仓库")
    config = runner(path, "config", "--local", "--list").lower()
    if "promisor=true" in config or "extensions.partialclone=" in config:
        _invalid("收集不允许用户仓库按需联网获取对象")


def _resolve(repo: Path, ref: str, runner: GitRunner) -> str:
    try:
        return _hash(runner(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip(), "HEAD")
    except CollectError as exc:
        if exc.code == 50000:
            raise CollectError(40001, "提交或 ref 不可检出") from exc
        raise


def _ancestor(repo: Path, earlier: str, later: str, runner: GitRunner):
    result = runner(repo, "rev-list", later, "--").splitlines()
    if earlier not in result:
        _invalid("提交不可达或提交范围不是祖先闭范围")


def code_version(*, progress=None) -> str:
    """Include uncommitted preparation source bytes, not just repository HEAD."""
    digest = hashlib.sha256()
    for path in sorted(BASE.glob("*.py")):
        if progress:
            progress()
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    head = GitRunner([], progress)(ROOT, "rev-parse", "--verify", "HEAD").strip()
    return head + "+preparation." + digest.hexdigest()


def _controlled_directory(path: Path, repo_source: str) -> Path:
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        _invalid("缓存目录不允许符号链接")
    resolved = path.resolve()
    if "://" not in repo_source:
        repo = Path(repo_source).resolve()
        if resolved == repo or repo in resolved.parents:
            _invalid("缓存不能写入用户仓库")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    return resolved


def _atomic_json(path: Path, value):
    content = _json(value)
    if path.is_symlink():
        _invalid("拒绝写入符号链接")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".collect-", delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _cache_read(path: Path, key: str, version: str):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_COMMAND_BYTES:
        return None
    try:
        cached = json.loads(path.read_bytes())
        payload = cached["payload"]
        if (cached["version"] != CACHE_VERSION or cached["key"] != key or cached["code_version"] != version
                or cached["sha256"] != _sha(_json(payload))):
            return None
        rows = payload["rows"]
        if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
            return None
        if len({row["commit_hash"] for row in rows}) != len(rows):
            return None
        for row in rows:
            _hash(row["commit_hash"], "cached hash")
            if row["is_bug_inducing"] not in (None, 0, 1) or row["is_test"] not in (0, 1):
                return None
        return payload
    except (OSError, ValueError, TypeError, KeyError):
        return None


def run(config: dict, *, allow_roots: list[str], protocol_whitelist: list[str],
        commit_hashes: list[str] | None = None, progress=None, cache_dir: Path | None = None) -> dict:
    """Return complete commits rows, summary, audit, config snapshot and actual inputs.

    Five transitions (done=0..5,total=5); repeated same-stage callbacks are cancel
    checkpoints. Incremental reuses only an exact validated source+HEAD+config+
    list+source-version JSON result, never stale labels from a previous HEAD.
    """
    phase = 0
    callback_error = None
    def checkpoint():
        nonlocal callback_error
        if progress:
            try:
                progress(PHASES[phase], phase, 5)
            except BaseException as exc:
                callback_error = exc
                raise
    def advance(value):
        nonlocal phase
        phase = value
        checkpoint()
    checkpoint()
    cfg = validate_config(config, allow_roots=allow_roots, protocol_whitelist=protocol_whitelist)
    roots = _roots(allow_roots)
    selected = None
    deduplicated = 0
    if commit_hashes is not None:
        if not isinstance(commit_hashes, list) or len(commit_hashes) > MAX_ROWS:
            _invalid("提交清单须为不超过行数上限的 list")
        values = [_hash(value, "commit_hashes") for value in commit_hashes]
        selected = sorted(set(values))
        deduplicated = len(values) - len(selected)
    runner = GitRunner(protocol_whitelist, checkpoint)
    source = cfg["repo_source"]
    # Never create snapshots or clones underneath a user's checkout, even when
    # that checkout itself was configured as an allowed root.
    controlled_roots = [root for root in roots if "://" in source or
                        not (root == Path(source) or Path(source) in root.parents)]
    if not controlled_roots:
        _invalid("需要用户仓库之外的受控允许根目录")
    cache = _controlled_directory(cache_dir, source) if cache_dir is not None else None
    # ExitStack-like explicit ownership: only this TemporaryDirectory is removed.
    temporary = None
    owned_snapshot = None
    succeeded = False
    try:
        advance(1)
        local_repo = Path(source) if "://" not in source else None
        fetch_audit = "disabled"
        remote = source if local_repo is None else ""
        if local_repo is not None:
            _repository(local_repo, roots, runner)
            if cfg["fetch_remote"]:
                remote = runner(local_repo, "config", "--get", "remote.origin.url", allowed_exit_codes=(0, 1)).strip()
                if not remote:
                    fetch_audit = "no_origin_local_snapshot"
        temporary = tempfile.TemporaryDirectory(prefix=".collect-clone-", dir=controlled_roots[0])
        controlled = Path(temporary.name)
        repo = controlled / "repository.git"
        if remote:
            url, runner.network_config = _url(remote, protocol_whitelist)
            runner.size_directory = repo
            # Remote configs/attributes/hooks are not inherited from user Git.
            # 始终完整 bare clone；start_time/end_time 只过滤输出提交，不影响历史范围。
            clone_args = ["clone", "--bare", "--no-local", "--template="]
            runner(controlled, *clone_args, "--", url, str(repo))
            fetch_audit = "new_controlled_clone"
        else:
            # Explicit file permission is restricted to this previously validated
            # local clone only. No hardlinks, templates or user working tree.
            local_runner = GitRunner(["file"], checkpoint, size_directory=repo)
            local_runner(controlled, "clone", "--bare", "--local", "--no-hardlinks", "--template=",
                         "--", str(local_repo), str(repo))
        runner.size_directory = None
        _repository(repo, roots, runner)
        head = _resolve(repo, cfg["branch"] or "HEAD", runner)
        if cfg["head_expect"] and head != cfg["head_expect"]:
            _invalid("HEAD 与 head_expect 不一致")
        for key in ("start_commit", "end_commit"):
            if cfg[key]:
                _resolve(repo, cfg[key], runner)
                _ancestor(repo, cfg[key], head, runner)
        if cfg["start_commit"] and cfg["end_commit"]:
            _ancestor(repo, cfg["start_commit"], cfg["end_commit"], runner)
        advance(2)
        metadata = importlib.import_module("preparation.01_extract_commits")
        szz = importlib.import_module("preparation.02_szz_labeling")
        features = importlib.import_module("preparation.03_extract_features")
        split = importlib.import_module("preparation.05_split_dataset")
        repo_name = Path(urlsplit(source).path).name.removesuffix(".git") if "://" in source else Path(source).name
        all_rows = metadata.extract_commits(repo, ref=head, repo_name=repo_name, runner=runner, progress=checkpoint)
        all_hashes = set(runner(repo, "rev-list", head, "--").splitlines())
        if selected is not None and not set(selected) <= all_hashes:
            _invalid("提交清单含选定 HEAD 不可达提交")
        lower = set(runner(repo, "rev-list", cfg["start_commit"], "--").splitlines()) if cfg["start_commit"] else set()
        upper = set(runner(repo, "rev-list", cfg["end_commit"], "--").splitlines()) if cfg["end_commit"] else all_hashes
        lower.discard(cfg["start_commit"])
        candidates = upper - lower
        if cfg["start_commit"]:
            # DAG range: keep only descendants of start, not sibling branches.
            descendants = set(runner(repo, "rev-list", "--ancestry-path", f"{cfg['start_commit']}..{head}", "--").splitlines())
            candidates &= descendants | {cfg["start_commit"]}
        targets = []
        for row in all_rows:
            checkpoint()
            h = row["commit_hash"]
            ts = datetime.strptime(row["committed_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).timestamp()
            if (h not in candidates or selected is not None and h not in selected
                    or cfg["start_time"] and ts < _epoch(cfg["start_time"])
                    or cfg["end_time"] and ts > _epoch(cfg["end_time"])):
                continue
            targets.append(row)
        if not targets:
            _invalid("输出提交范围为空")
        if len(targets) > MAX_ROWS:
            _invalid("输出提交行数超限")
        labeled_at = datetime.fromtimestamp(int(runner(repo, "show", "-s", "--format=%ct", head).strip()), UTC).isoformat().replace("+00:00", "Z")
        snapshot_config = {**cfg, "feature_version": features.FEATURE_VERSION, "resolvedHEAD": head,
                           "szz_version": SZZ_VERSION, "labeled_at": labeled_at,
                           "range": {k: cfg[k] for k in ("start_time", "end_time", "start_commit", "end_commit")},
                           "commit_list_sha256": _sha(_json(selected)) if selected is not None else None}
        version = code_version(progress=checkpoint)
        key = _sha(_json({"source": source, "head": head, "config": snapshot_config, "list": selected, "code": version}))
        cache_path = cache / (key + ".json") if cache else None
        payload = _cache_read(cache_path, key, version) if cache_path and cfg["mode"] == "incremental" else None
        audit = {"deduplicated": deduplicated, "skipped": {"merges": len(all_hashes) - len(all_rows),
                 "outside_output_range": len(all_rows) - len(targets)}, "stage_errors": [],
                 "head_check": "matched" if cfg["head_expect"] else "not_requested", "fetch": fetch_audit,
                 "cache": {"hit": payload is not None, "strategy": "exact_source_head_config_list_version_json" if cache else "hash_idempotent_full_parse"}}
        if payload is not None:
            advance(3)
            advance(4)
            advance(5)
            rows = payload["rows"]
            summary = payload["summary"]
            audit.update(szz=payload["szz"], boundary=payload["boundary"])
        else:
            advance(3)
            fixes = [row for row in all_rows if szz.is_fix_commit(row["message"])]
            result = szz.run_method(cfg["szz_method"], repo, all_rows, fixes, 0, runner=runner,
                                    progress=checkpoint, nullable=True, verbose=False)
            szz_audit = {k: result[k] for k in ("fix_total", "unresolved", "unresolved_hashes", "unresolved_reasons", "out_of_window", "no_parent", "diff_failed", "blame_calls")}
            szz_audit["label_policy"] = "no_success_all_null; successful_pass_non_introducers_zero; unresolved_repairs_null"
            advance(4)
            history = features.scan_history(repo, ref=head, runner=runner, progress=checkpoint)
            if any(row["commit_hash"] not in history for row in targets):
                raise CollectError(50000, "提交清单与特征历史不一致")
            raw = features.compute_raw(targets, history, features.HistoryIndex(history, progress=checkpoint), szz.is_fix_commit,
                                       repo, verbose=False, runner=runner, progress=checkpoint)
            values = features.apply_contract(raw)
            rows = []
            for row, value in zip(targets, values, strict=True):
                checkpoint()
                label = result["label_values"][row["commit_hash"]]
                rows.append({**row, **{field: value[field] for field in features.FEATURE_FIELDS},
                             "is_bug_inducing": label, "labeled_at": labeled_at if label is not None else None,
                             "is_test": 0, "label_method": cfg["szz_method"] if label is not None else None})
            advance(5)
            cut = split.split_index(len(rows), cfg["split_ratio"])
            if len(rows) == 1:
                cut = 1
                boundary = {"reason": "single_commit_no_two_sided_split", "train_end": rows[0]["committed_at"], "test_start": None}
            else:
                failures = split.validate_split(rows[:cut], rows[cut:], len(rows))
                if failures:
                    _invalid("; ".join(failures))
                boundary = {"train_end": rows[cut - 1]["committed_at"], "test_start": rows[cut]["committed_at"]}
            for i, row in enumerate(rows):
                checkpoint()
                row["is_test"] = int(i >= cut)
                row["committed_at"] = row["committed_at"].replace(" ", "T") + "Z"
            positives = sum(row["is_bug_inducing"] == 1 for row in rows)
            negatives = sum(row["is_bug_inducing"] == 0 for row in rows)
            summary = {"rows": len(rows), "labeled_rows": positives + negatives, "positive_rows": positives,
                       "negative_rows": negatives, "unlabeled_rows": len(rows) - positives - negatives,
                       "head_hash": head, "train_rows": cut, "test_rows": len(rows) - cut}
            audit.update(szz=szz_audit, boundary=boundary)
            payload = {"rows": rows, "summary": summary, "szz": szz_audit, "boundary": boundary}
            if cache_path and cfg["mode"] == "incremental":
                _atomic_json(cache_path, {"version": CACHE_VERSION, "key": key, "code_version": version,
                                          "sha256": _sha(_json(payload)), "payload": payload})
        # This is an actual input artifact, not a hash invented from the source URL.
        snapshot = {"repo_source": source, "head_hash": head, "commits": all_rows}
        content = _json(snapshot)
        if cache:
            snapshots = _controlled_directory(cache / "snapshots" / _sha(content), source)
        else:
            snapshots = Path(tempfile.mkdtemp(prefix=".collect-snapshot-", dir=controlled_roots[0]))
            owned_snapshot = snapshots
        snapshot_path = snapshots / "repository_snapshot.json"
        _atomic_json(snapshot_path, snapshot)
        checkpoint()
        succeeded = True
        return {"rows": rows, "summary": summary, "audit": audit, "config": snapshot_config,
                "inputs": [{"name": "repository_snapshot.json", "path": str(snapshot_path),
                            "sha256": _sha(content), "rows": len(all_rows)}]}
    except Exception as exc:
        if exc is callback_error:
            raise
        error = exc if isinstance(exc, CollectError) else CollectError(50000, f"collect {PHASES[phase]} 阶段运行失败")
        error.audit = {"stage_errors": [{"phase": PHASES[phase], "code": error.code, "message": error.message}]}
        if error is exc:
            raise
        raise error from exc
    finally:
        if temporary is not None:
            temporary.cleanup()
        if owned_snapshot is not None and not succeeded:
            shutil.rmtree(owned_snapshot)


def _file_services():
    # Only the known backend source directory, never arbitrary user sys.path.
    for source in (ROOT / "backend", ROOT / "data_model"):
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    from app.services import file_contracts, output_store
    return file_contracts, output_store


def encode_rows(rows: list[dict], format: str) -> bytes:
    """输出 collected_commits 契约二维表：不含 Kamei14、不含 is_test。

    内部特征仅用于 SZZ/切分校验，不对外 handoff；训练阶段从绑定仓库现算。
    """
    contracts, _ = _file_services()
    columns = contracts.COLLECTED_COMMITS_COLUMNS
    cells = []
    for row in rows:
        record = {key: "" if value is None else value for key, value in row.items()}
        record.setdefault("repo_url", "")
        record.setdefault("fix_commit_hash", (row.get("fix_commit_hash") or ""))
        record.setdefault("label_source", "git_szz")
        record.setdefault("source_type", "git_repo")
        record.setdefault("label_method", "")
        cells.append({key: record.get(key, "") for key in columns})
    return contracts.encode_table(columns, cells, format)


def _publish(result: dict, out: Path, format: str, *, version: str | None = None):
    contracts, outputs = _file_services()
    outputs.OUTPUT_ROOT = out.resolve()  # CLI process only; API never calls this helper.
    job_id = str(uuid4())
    artifacts = {f"collect_commits_{job_id}.{format}": encode_rows(result["rows"], format),
                 f"collect_summary_{job_id}.json": _json(result["summary"]),
                 f"collect_audit_{job_id}.json": _json(result["audit"])}
    for item in result["inputs"]:
        if item.get("name") == "repository_snapshot.json" and item.get("path"):
            content = Path(item["path"]).read_bytes()
            if _sha(content) != item["sha256"]:
                _invalid("仓库快照 checksum 不一致")
            artifacts[f"collect_repository_snapshot_{job_id}.json"] = content
    inputs = [{key: value for key, value in item.items() if key != "path"} for item in result["inputs"]]
    return outputs.publish_output("collect", artifacts, inputs=inputs, config=result["config"],
                                  job_id=job_id, code_version=version or code_version())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Independent Git collect/run and verified export")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run")
    command.add_argument("--repo", required=True)
    command.add_argument("--branch")
    command.add_argument("--name", required=True)
    command.add_argument("--start")
    command.add_argument("--end")
    command.add_argument("--start-commit")
    command.add_argument("--end-commit")
    command.add_argument("--head-expect")
    command.add_argument("--mode", choices=("full", "incremental"), default="incremental")
    command.add_argument("--fetch-remote", choices=("true", "false"), default="true")
    command.add_argument("--szz-method", choices=("szz_v1", "szz_lite"), default="szz_v1")
    command.add_argument("--split-ratio", type=float, default=0.7)
    command.add_argument("--format", choices=("csv", "xlsx"), default="csv")
    command.add_argument("--out", required=True, type=Path)
    command.add_argument("--allow-root", action="append", required=True)
    command.add_argument("--protocol", action="append", default=[])
    export = sub.add_parser("export")
    export.add_argument("--input", required=True, type=Path)
    export.add_argument("--format", required=True, choices=("csv", "xlsx"))
    export.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    _file_services()
    from app.errors import AppError
    try:
        if args.command == "run":
            result = run({"repo_source": args.repo, "branch": args.branch, "dataset_name": args.name,
                          "start_time": args.start, "end_time": args.end, "start_commit": args.start_commit,
                          "end_commit": args.end_commit, "head_expect": args.head_expect, "mode": args.mode,
                          "fetch_remote": args.fetch_remote == "true", "szz_method": args.szz_method,
                          "split_ratio": args.split_ratio, "format": args.format},
                         allow_roots=args.allow_root, protocol_whitelist=args.protocol,
                         cache_dir=args.out.resolve() / ".collect-cache")
            published = _publish(result, args.out, args.format)
        else:
            contracts, _ = _file_services()
            path = args.input.resolve(strict=True)
            content = path.read_bytes()
            manifest = contracts.verify_manifest(path.name, content, path.with_suffix(".manifest.json").read_bytes())
            if manifest["module"] != "collect" or manifest["config"].get("feature_version") != "v1":
                _invalid("export 需要 collect/v1 companion manifest")
            columns, rows = contracts.read_table(path.name, content)
            if tuple(columns) != contracts.COLLECTED_COMMITS_COLUMNS:
                _invalid("export 表格列序不符合 collected_commits 契约")
            # No Git or SZZ during export; the verified source code identity is retained.
            result = {"rows": rows, "summary": {"rows": len(rows)}, "audit": {"export_only": True},
                      "config": {**manifest["config"], "format": args.format},
                      "inputs": [{"name": path.name, "sha256": _sha(content), "rows": len(rows)}]}
            published = _publish(result, args.out or path.parent.parent, args.format,
                                 version=manifest["code_version"])
        print(json.dumps(published, ensure_ascii=False))
        return 0
    except (CollectError, OSError, AppError) as exc:
        message = getattr(exc, "message", "文件读写失败")
        print(json.dumps({"code": getattr(exc, "code", 40001), "message": message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

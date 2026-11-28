"""缺陷定位：读取本地仓库缓存，定位高风险改动行并给出修复建议。"""

from __future__ import annotations

from app.errors import AppError
from app.models import User
from app.services import predict
from data_model import gitops

NOISE = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "go.sum", "Cargo.lock"}
RISKY = ("[", ".get(", "None", "null", "==", "!=", "except", "return")


def _suggestion(kind: str, content: str) -> str:
    if kind == "removed":
        return "确认删除的逻辑是否有替代实现，并检查调用方是否仍依赖该分支。"
    if any(token in content for token in RISKY):
        return "补充空值、越界与异常判断，避免直接下标或宽泛捕获。"
    return "为该改动补充单元测试，覆盖正常、异常与回滚路径。"


def localize(db, user: User, job_id: str, commit_hash: str) -> dict:
    _, _, ref = predict.resolve_rows(db, user, job_id)
    repo_info = ref.get("repo") or {}
    if not repo_info.get("repo_url"):
        raise AppError(40901, "该结果缺少仓库信息，无法定位", {"reason": "no_repo"})
    try:
        info = gitops.parse_repo_url(repo_info["repo_url"])
    except ValueError as exc:
        raise AppError(40001, str(exc)) from exc
    from git import Repo

    path = gitops.cache_dir(info)
    if not path.exists():
        raise AppError(40901, "本地仓库缓存不可用", {"reason": "commit_missing"})
    repo = Repo(path)
    try:
        commit = repo.commit(commit_hash)
    except Exception:  # noqa: BLE001
        raise AppError(40901, "本地仓库缓存缺少该提交", {"reason": "commit_missing"})
    hunks = gitops.diff_hunks(commit)
    files = []
    for file, lines in hunks.items():
        if file in NOISE:
            continue
        changed = [line for line in lines if line["type"] != "context"]
        if not changed:
            continue
        score = sum(1.0 if line["type"] == "removed" else 0.6 for line in changed) / len(changed)
        entries = []
        for line in lines[:200]:
            is_changed = line["type"] != "context"
            suspicious = is_changed and (
                line["type"] == "removed" or any(token in line["content"] for token in RISKY)
            )
            entries.append({
                "no": line["no"],
                "type": line["type"],
                "content": line["content"][:400],
                "suspicious": suspicious,
                "suggestion": _suggestion(line["type"], line["content"]) if suspicious else "",
            })
        files.append({"path": file, "suspicious_score": round(score, 3), "lines": entries})
    files.sort(key=lambda item: item["suspicious_score"], reverse=True)
    return {"files": files}

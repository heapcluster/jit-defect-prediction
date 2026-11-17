"""针对缺陷的修复建议：LLM 可用时生成，否则回退基于定位结果的可执行模板。"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app import config
from app.services import risk_summary

logger = logging.getLogger("backend.fix_suggestion")


def _facts(
    commit_message: str,
    risk_score: float | None,
    model_line: str | None,
    features: dict | None,
    explanation: list[dict] | None,
    localization: dict | None,
    historical_fixes: list[dict] | None,
) -> dict:
    files = []
    for item in (localization or {}).get("files", [])[:3]:
        lines = [
            {
                "number": line.get("number"),
                "content": (line.get("content") or "")[:160],
                "score": line.get("score", 0),
            }
            for line in (item.get("added_lines") or item.get("lines") or [])
        ]
        lines.sort(key=lambda line: line.get("score") or 0, reverse=True)
        files.append(
            {
                "path": item.get("path"),
                "score": item.get("score"),
                "reasons": item.get("reasons"),
                "lines": lines[:8],
            }
        )
    return {
        "commit_message": (commit_message or "")[:1200],
        "risk_score": round(float(risk_score), 4) if risk_score is not None else None,
        "model_line": model_line,
        "top_factors": risk_summary.feature_phrases(features, explanation),
        "top_files": files,
        "historical_fix_messages": [
            (item.get("message") or "")[:160] for item in (historical_fixes or [])[:2]
        ],
    }


def template_suggestions(facts: dict) -> list[str]:
    files = facts.get("top_files") or []
    suggestions: list[str] = []
    if files:
        first = files[0]
        line = (first.get("lines") or [{}])[0].get("number")
        where = f"{first.get('path')}" + (f" 第 {line} 行附近" if line else "")
        suggestions.append(f"优先复核 {where}的新增/修改逻辑，确认边界条件与异常路径。")
    if files:
        suggestions.append(f"为 {files[0].get('path')} 的新增分支补充单元测试，覆盖空值与异常输入。")
    factors = "、".join(facts.get("top_factors") or [])
    if factors:
        suggestions.append(f"结合「{factors}」复核改动范围，必要时拆分提交或缩小影响面。")
    else:
        suggestions.append("检查空值处理、资源释放与错误提示是否覆盖本次改动。")
    return suggestions[:3]


def _llm_suggestions(facts: dict) -> list[str] | None:
    if not (config.LLM_BASE_URL and config.LLM_API_KEY and config.LLM_MODEL):
        return None
    body = json.dumps(
        {
            "model": config.LLM_MODEL,
            "temperature": 0.2,
            "max_tokens": 300,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是资深代码审查员。只根据给定事实给出 2-3 条中文修复建议，"
                        "每条不超过40字、必须可执行；不要编造事实中没有的文件、行号或 API；"
                        "只输出 JSON 字符串数组，不要 Markdown。"
                    ),
                },
                {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        f"{config.LLM_BASE_URL}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "jit-fix-suggestion",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as resp:
            data = json.load(resp)
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        content = str(content).strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        parsed = json.loads(content)
        if isinstance(parsed, list):
            items = [" ".join(str(item).split())[:80] for item in parsed if str(item).strip()]
            return items[:3] or None
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
        logger.warning("llm fix suggestions unavailable: %s", exc)
    return None


def suggestions_for(
    *,
    commit_message: str,
    risk_score: float | None,
    model_line: str | None,
    features: dict | None,
    explanation: list[dict] | None,
    localization: dict | None,
    historical_fixes: list[dict] | None = None,
) -> list[str]:
    facts = _facts(
        commit_message,
        risk_score,
        model_line,
        features,
        explanation,
        localization,
        historical_fixes,
    )
    return _llm_suggestions(facts) or template_suggestions(facts)

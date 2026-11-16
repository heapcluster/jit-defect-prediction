"""风险一句话总结：所有架构/模型共用，LLM 可用时润色，不可用时回退确定性模板。"""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request

from app import config

logger = logging.getLogger("backend.risk_summary")

_LINE_LABELS = {"expert": "专家特征", "semantic": "语义", "fused": "融合", "e2e": "端到端"}
_cache: dict[tuple, str] = {}
_lock = threading.Lock()


def _level(score: float) -> str:
    if score >= config.HIGH_RISK_THRESHOLD:
        return "高"
    if score >= config.MID_RISK_THRESHOLD:
        return "中"
    return "低"


def _feature_phrases(features: dict | None, explanation: list[dict] | None) -> list[str]:
    if explanation:
        positives = [
            item.get("label") or item.get("feature", "")
            for item in explanation
            if item.get("direction") == "increase"
        ]
        phrases = positives or [item.get("label") or item.get("feature", "") for item in explanation]
        return [p for p in phrases if p][:3]
    if not features:
        return []

    def num(name: str) -> float:
        return float(features.get(name) or 0)

    phrases: list[str] = []
    if num("nf") >= 1.6:
        phrases.append("改动文件较多")
    if num("la") >= 4:
        phrases.append("代码改动量较大")
    if num("ld") >= 3:
        phrases.append("删除代码较多")
    if num("entropy") >= 2:
        phrases.append("改动较分散")
    if num("ndev") >= 1:
        phrases.append("涉及多名开发者")
    if num("fix") >= 1:
        phrases.append("历史含修复语义")
    return phrases[:3]


def template_summary(
    *,
    model_name: str,
    model_line: str,
    risk_score: float,
    features: dict | None,
    explanation: list[dict] | None,
    localization: dict | None,
) -> str:
    level = _level(risk_score)
    line_label = _LINE_LABELS.get(model_line, model_line or "模型")
    factors = _feature_phrases(features, explanation)
    factor_text = "、".join(factors) if factors else "提交级特征未显示突出风险因子"
    files = [
        item.get("path", "")
        for item in (localization or {}).get("files", [])
        if item.get("path")
    ][:2]
    if level == "高":
        tail = f"；建议优先审查 {files[0]} 等 {len(files)} 个文件" if files else "；建议优先复核改动文件"
    elif level == "中":
        tail = f"；建议抽查 {files[0]} 等文件" if files else "；建议抽查改动文件"
    else:
        tail = "；可按常规流程复核"
    return f"该{line_label}模型判为{level}风险（{risk_score:.2f}）：{factor_text}{tail}。"


def _llm_summary(facts: dict) -> str | None:
    if not (config.LLM_BASE_URL and config.LLM_API_KEY and config.LLM_MODEL):
        return None
    body = json.dumps(
        {
            "model": config.LLM_MODEL,
            "temperature": 0.2,
            "max_tokens": 160,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是软件缺陷预测系统的代码审查助手。只根据给定事实写一句中文风险结论，"
                        "不超过80字；不要编造文件、行号或指标；不要使用 Markdown。"
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
            "User-Agent": "jit-risk-summary",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as resp:
            data = json.load(resp)
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        content = " ".join(str(content).split()).strip()
        return content[:160] or None
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
        logger.warning("llm summary unavailable: %s", exc)
        return None


def summary_for(
    *,
    commit_hash: str,
    model_name: str | None,
    model_line: str | None,
    risk_score: float | None,
    features: dict | None,
    explanation: list[dict] | None,
    localization: dict | None = None,
) -> str | None:
    """生成一句话风险总结；风险分为空时返回 None。"""
    if risk_score is None or not model_name:
        return None
    files = tuple(
        item.get("path", "") for item in (localization or {}).get("files", [])[:3]
    )
    key = (commit_hash, model_name, round(float(risk_score), 4), files)
    with _lock:
        cached = _cache.get(key)
    if cached:
        return cached
    template = template_summary(
        model_name=model_name,
        model_line=model_line or "",
        risk_score=float(risk_score),
        features=features,
        explanation=explanation,
        localization=localization,
    )
    facts = {
        "model_name": model_name,
        "model_line": model_line,
        "risk_score": round(float(risk_score), 4),
        "risk_level": _level(float(risk_score)),
        "top_factors": _feature_phrases(features, explanation),
        "top_files": list(files),
    }
    summary = _llm_summary(facts) or template
    with _lock:
        _cache[key] = summary
    return summary

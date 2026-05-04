"""High-level compression API.

Strategies:
  - "sns"        : ordered regex SNS rewrite rules (fast, dependency-light).
  - "llmlingua2" : optional LLMLingua-2 bridge (heavyweight, falls back to SNS).
  - "gist"       : gisting stub (always falls back to SNS unless wired up).
  - "auto"       : classify the prompt, then pick a strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

from . import sns_rules, classifier, llmlingua_bridge, gist
from .tokenizers import savings

Strategy = Literal["auto", "sns", "llmlingua2", "gist"]


@dataclass
class CompressionResult:
    original: str
    compressed: str
    strategy: str
    classified_as: str | None
    rules_applied: list[dict]
    stats: dict
    warning: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _strategy_for_class(cls: str) -> str:
    # Heuristic mapping: SNS works well for code/qa; for reasoning/creative we
    # prefer LLMLingua-2 (which preserves discourse better) but fall back to
    # SNS if it isn't installed. The bridge handles fallback transparently.
    if cls in ("reasoning", "creative"):
        return "llmlingua2"
    return "sns"


def compress(prompt: str, strategy: Strategy = "auto") -> str:
    """Public entry point. Returns the compressed string only.

    For richer output (rules applied, warnings, token counts) use
    `compress_detailed()`.
    """
    return compress_detailed(prompt, strategy).compressed


def compress_detailed(prompt: str, strategy: Strategy = "auto") -> CompressionResult:
    classified: str | None = None
    chosen = strategy
    if strategy == "auto":
        classified = classifier.classify(prompt)
        chosen = _strategy_for_class(classified)

    warning: str | None = None
    rules_applied: list[dict] = []

    if chosen == "sns":
        compressed, hits = sns_rules.apply_rules(prompt, trace=True)
        rules_applied = [
            {"id": h.rule_id, "category": h.category, "before": h.before, "after": h.after}
            for h in hits
        ]
    elif chosen == "llmlingua2":
        result = llmlingua_bridge.compress_with_llmlingua(prompt)
        compressed = result.text
        warning = result.warning
        if result.used == "sns-fallback":
            # Surface the actual rule trace so explain mode still shows work.
            _, hits = sns_rules.apply_rules(prompt, trace=True)
            rules_applied = [
                {"id": h.rule_id, "category": h.category, "before": h.before, "after": h.after}
                for h in hits
            ]
        chosen = result.used
    elif chosen == "gist":
        result = gist.compress_with_gist(prompt)
        compressed = result.text
        warning = result.warning
        if result.used == "sns-fallback":
            _, hits = sns_rules.apply_rules(prompt, trace=True)
            rules_applied = [
                {"id": h.rule_id, "category": h.category, "before": h.before, "after": h.after}
                for h in hits
            ]
        chosen = result.used
    else:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    stats = savings(prompt, compressed)
    return CompressionResult(
        original=prompt,
        compressed=compressed,
        strategy=chosen,
        classified_as=classified,
        rules_applied=rules_applied,
        stats=stats,
        warning=warning,
    )


def explain(prompt: str, strategy: Strategy = "auto") -> dict:
    """Return a detailed dict suitable for diff/explain UIs."""
    result = compress_detailed(prompt, strategy)
    return result.to_dict()

"""Optional LLMLingua-2 bridge.

Tries to import `llmlingua.PromptCompressor` and run the recommended
LLMLingua-2 setup. If the dependency or model is unavailable we fall back to
the SNS engine and emit a structured warning so callers can surface it.

Reference: Microsoft LLMLingua / LLMLingua-2 (https://github.com/microsoft/LLMLingua).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

from . import sns_rules


@dataclass
class LLMLinguaResult:
    text: str
    used: str  # "llmlingua-2" | "sns-fallback"
    warning: str | None = None
    meta: dict | None = None


_DEFAULT_MODEL = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"


def _load_compressor(model_name: str = _DEFAULT_MODEL) -> Any | None:
    try:
        from llmlingua import PromptCompressor  # type: ignore
    except ImportError:
        return None
    try:
        return PromptCompressor(
            model_name=model_name,
            use_llmlingua2=True,
        )
    except Exception as e:  # pragma: no cover - environment-specific
        warnings.warn(f"LLMLingua loaded but model init failed: {e}", RuntimeWarning)
        return None


def compress_with_llmlingua(
    prompt: str,
    *,
    rate: float = 0.5,
    force_tokens: list[str] | None = None,
    model_name: str = _DEFAULT_MODEL,
) -> LLMLinguaResult:
    """Compress with LLMLingua-2; fall back to SNS rules on failure.

    `rate` is target retention ratio (0.5 = aim to keep 50% of tokens).
    """
    compressor = _load_compressor(model_name)
    if compressor is None:
        out, _ = sns_rules.apply_rules(prompt)
        return LLMLinguaResult(
            text=out,
            used="sns-fallback",
            warning=(
                "LLMLingua not installed or model unavailable. "
                "Install with `pip install llmlingua` and ensure the model "
                f"`{model_name}` can be downloaded."
            ),
        )
    try:
        result = compressor.compress_prompt(
            prompt,
            rate=rate,
            force_tokens=force_tokens or ["\n", "?", "."],
        )
        text = result.get("compressed_prompt", prompt) if isinstance(result, dict) else str(result)
        meta = result if isinstance(result, dict) else None
        return LLMLinguaResult(text=text, used="llmlingua-2", meta=meta)
    except Exception as e:  # pragma: no cover
        out, _ = sns_rules.apply_rules(prompt)
        return LLMLinguaResult(
            text=out,
            used="sns-fallback",
            warning=f"LLMLingua call failed at runtime: {e}",
        )

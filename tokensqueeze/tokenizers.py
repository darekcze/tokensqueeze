"""Token counting utilities.

Uses tiktoken when available; falls back to a simple word/regex approximation
calibrated to roughly match cl100k_base on prose. Optionally supports
HuggingFace transformers tokenizers when the user passes one.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

_FALLBACK_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@lru_cache(maxsize=8)
def _try_tiktoken(encoding_name: str):
    try:
        import tiktoken  # type: ignore
        return tiktoken.get_encoding(encoding_name)
    except Exception:
        return None


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """Best-effort token counter.

    Tries tiktoken first; falls back to regex-based word+punct counting with a
    1.3x multiplier — empirically near cl100k_base for English prose, and a
    safe upper-ish bound for shorter prompts.
    """
    if not text:
        return 0
    enc = _try_tiktoken(encoding)
    if enc is not None:
        try:
            return len(enc.encode(text))
        except Exception:
            pass
    base = len(_FALLBACK_TOKEN_RE.findall(text))
    # Add a small multiplier for sub-word splits commonly produced by BPE.
    return max(1, int(round(base * 1.3)))


def count_tokens_with(text: str, tokenizer: Any) -> int:
    """Count tokens using a user-supplied tokenizer (e.g. HF AutoTokenizer)."""
    if hasattr(tokenizer, "encode"):
        return len(tokenizer.encode(text))
    if hasattr(tokenizer, "tokenize"):
        return len(tokenizer.tokenize(text))
    raise TypeError("Unsupported tokenizer; needs .encode() or .tokenize()")


def savings(original: str, compressed: str, encoding: str = "cl100k_base") -> dict:
    """Return token counts and reduction ratio."""
    o = count_tokens(original, encoding)
    c = count_tokens(compressed, encoding)
    return {
        "original_tokens": o,
        "compressed_tokens": c,
        "saved_tokens": o - c,
        "reduction": (o - c) / o if o else 0.0,
        "encoding": encoding,
    }

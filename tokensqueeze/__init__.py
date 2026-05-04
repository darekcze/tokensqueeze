"""TokenSqueeze: prompt compression for LLMs.

Public API:
    compress(prompt, strategy="auto") -> str
    explain(prompt) -> dict
    count_tokens(text, encoding="cl100k_base") -> int
"""
from .compress import compress, explain
from .tokenizers import count_tokens

__version__ = "0.1.0"
__all__ = ["compress", "explain", "count_tokens", "__version__"]

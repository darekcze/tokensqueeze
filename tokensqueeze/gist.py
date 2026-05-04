"""Gisting strategy stub.

Prompt gisting (Mu et al., 2023, "Learning to Compress Prompts with Gist Tokens")
trains a model to compress an instruction into a small set of "gist" tokens
that are then prepended to inputs at inference. This is an architecture-level
technique requiring a fine-tuned model — we *do not* attempt to fake it here.

This module documents the requirements and returns an SNS fallback with a
structured warning so callers can decide what to do.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import sns_rules


GIST_REQUIREMENTS = """\
Gisting requires:
  1. A causal LM (e.g. LLaMA, T5) fine-tuned with the gist mask described in
     Mu et al. (2023). Off-the-shelf base models do not produce valid gist
     tokens.
  2. A vocabulary-extension token (the "gist token") whose attention mask is
     restricted to act as an information bottleneck during fine-tuning.
  3. Inference plumbing that prepends the gist tokens (instead of the full
     instruction) to each new input.

Because no public, drop-in 'gisting' compressor exists that works on arbitrary
prompts without the fine-tuned model, this module returns an SNS fallback and
a warning. Train your own gist model following the paper, then plug a
predictor into `gist.py:compress_with_gist`.
"""


@dataclass
class GistResult:
    text: str
    used: str  # "gist" | "sns-fallback"
    warning: str | None = None


def compress_with_gist(prompt: str, *, model_path: str | None = None) -> GistResult:
    """Always falls back unless the user has wired up a trained gist model.

    Hook point: subclass / monkeypatch this function with one that loads a
    user-trained gist model from `model_path` and returns the gist-token
    sequence rendered to text.
    """
    if model_path:
        try:
            return _user_gist_model(prompt, model_path)
        except Exception as e:
            out, _ = sns_rules.apply_rules(prompt)
            return GistResult(
                text=out,
                used="sns-fallback",
                warning=f"Gist model at {model_path} failed: {e}. {GIST_REQUIREMENTS}",
            )
    out, _ = sns_rules.apply_rules(prompt)
    return GistResult(
        text=out,
        used="sns-fallback",
        warning=(
            "Gisting requires a fine-tuned model and is not available out of the "
            "box. Falling back to SNS. " + GIST_REQUIREMENTS
        ),
    )


def _user_gist_model(prompt: str, model_path: str) -> GistResult:
    """Placeholder — override in user code.

    The expected contract: load the trained gist model from `model_path`,
    encode `prompt`, return GistResult(text=<gist-token-rendering>, used="gist").
    """
    raise NotImplementedError(
        "No bundled gist model. Implement _user_gist_model() with your trained "
        "checkpoint, or use strategy='sns' / strategy='llmlingua2' instead."
    )

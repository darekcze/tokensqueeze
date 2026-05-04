"""End-to-end compression tests."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tokensqueeze import compress, count_tokens
from tokensqueeze.compress import compress_detailed


def reduction(original: str, compressed: str) -> float:
    o = count_tokens(original)
    c = count_tokens(compressed)
    return (o - c) / o if o else 0.0


def test_canonical_prime_sample_hits_40_percent():
    """The README quickstart example must yield >=40% reduction."""
    p = "Write a Python function that checks if a number is prime"
    c = compress(p)
    r = reduction(p, c)
    assert r >= 0.40, f"Expected >=40% reduction, got {r:.2%}; out={c!r}"


def test_compress_returns_string():
    out = compress("hello world")
    assert isinstance(out, str)


def test_strategy_sns_explicit():
    p = "Please write a function that takes a list of numbers and returns the sum"
    out = compress(p, strategy="sns")
    assert isinstance(out, str)
    assert reduction(p, out) > 0.0


def test_strategy_auto_classifies():
    p = "Write a Python function that reverses a string"
    result = compress_detailed(p, strategy="auto")
    assert result.classified_as in {"code", "qa", "reasoning", "creative"}


def test_strategy_llmlingua_falls_back_gracefully():
    """Without llmlingua installed the bridge must fall back to SNS with a warning."""
    p = "Explain quantum entanglement step by step in simple terms."
    result = compress_detailed(p, strategy="llmlingua2")
    # The strategy actually used is reported back; either it's the real model,
    # or the fallback. The 'sns-fallback' path must include a warning.
    assert result.strategy in {"llmlingua-2", "sns-fallback"}
    if result.strategy == "sns-fallback":
        assert result.warning


def test_strategy_gist_falls_back_with_requirements():
    p = "Summarize the article."
    result = compress_detailed(p, strategy="gist")
    assert result.strategy == "sns-fallback"
    assert "Gisting" in (result.warning or "")


def test_unknown_strategy_raises():
    with pytest.raises(ValueError):
        compress("hi", strategy="bogus")  # type: ignore[arg-type]


def test_cli_json_smoke():
    """Run the CLI as a subprocess and parse the JSON output."""
    cmd = [sys.executable, "-m", "tokensqueeze.cli", "--json", "--strategy", "sns"]
    proc = subprocess.run(
        cmd,
        input="Write a Python function that checks if a number is prime",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert "compressed" in payload
    assert payload["tokens"]["original"] >= payload["tokens"]["compressed"]


def test_cli_text_smoke():
    cmd = [sys.executable, "-m", "tokensqueeze.cli", "--strategy", "sns", "--quiet"]
    proc = subprocess.run(
        cmd,
        input="Please write a JavaScript function that returns the sum of an array",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip()


def test_cli_explain_writes_rule_trace_to_stderr():
    cmd = [sys.executable, "-m", "tokensqueeze.cli", "--strategy", "sns", "--explain"]
    proc = subprocess.run(
        cmd,
        input="Please write a Python function that reverses a string",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "rules applied" in proc.stderr


def test_explain_function_returns_dict_with_rule_count():
    from tokensqueeze.sns_rules import explain
    result = explain("Please write a function that returns the result as JSON")
    assert "rules_applied" in result
    assert result["rule_count"] >= 1
    assert result["output"] != result["input"]


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "x",
        "Hello.",
        "已经很短",
        "Funkcja która zwraca listę",
    ],
)
def test_compress_handles_short_inputs(prompt):
    out = compress(prompt)
    assert isinstance(out, str)

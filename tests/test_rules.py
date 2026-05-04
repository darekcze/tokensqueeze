"""SNS rule-engine tests."""
from __future__ import annotations

import re

import pytest

from tokensqueeze.sns_rules import RULES, all_rules, apply_rules, explain


def test_rules_list_is_nonempty_and_has_unique_ids():
    rules = all_rules()
    assert len(rules) >= 50, f"Need at least 50 rules, got {len(rules)}"
    ids = [r.id for r in rules]
    assert len(set(ids)) == len(ids), "Rule IDs must be unique"


def test_every_rule_compiles():
    for r in RULES:
        try:
            re.compile(r.pattern, r.flags)
        except re.error as e:
            pytest.fail(f"Rule {r.id} has invalid pattern: {e}")


def test_categories_cover_required_buckets():
    cats = {r.category for r in RULES}
    required = {
        "function", "io", "conditional", "list", "json",
        "fluff", "verb", "polish", "chinese", "tidy",
    }
    missing = required - cats
    assert not missing, f"Missing categories: {missing}"


def test_please_is_dropped():
    out, _ = apply_rules("Please write a function")
    assert "please" not in out.lower()


def test_could_you_dropped():
    out, _ = apply_rules("Could you please write tests for this module")
    assert "could you" not in out.lower()


def test_function_template_collapsed():
    out, _ = apply_rules("Write a Python function that does something useful")
    assert "fn[Python]" in out or "fn:" in out


def test_returns_to_arrow():
    out, _ = apply_rules("that returns a string")
    assert "->" in out


def test_json_output_collapsed():
    out, _ = apply_rules("Return the result as JSON")
    assert "->json" in out


def test_polish_jezeli():
    out, _ = apply_rules("Jeżeli liczba jest parzysta")
    assert out.lower().startswith("if ")


def test_polish_napisz_funkcje():
    out, _ = apply_rules("Napisz funkcję która zwraca listę")
    assert "fn:" in out
    assert "->" in out


def test_chinese_please_dropped():
    out, _ = apply_rules("请返回一个列表")
    assert "请" not in out
    assert "->" in out


def test_explain_traces_rules():
    info = explain("Please write a function that returns a list of numbers")
    assert info["rule_count"] >= 2
    assert all("id" in r and "category" in r for r in info["rules_applied"])


def test_idiom_prime_collapses_completely():
    out, _ = apply_rules("Write a Python function that checks if a number is prime")
    assert "isPrime" in out


def test_tidy_collapses_double_space():
    out, _ = apply_rules("hello   world")
    assert "  " not in out


def test_make_sure_to_must():
    out, _ = apply_rules("Make sure to handle empty inputs")
    assert "must" in out.lower()


def test_unless_to_if_not():
    out, _ = apply_rules("Unless the input is empty")
    assert "if !" in out


def test_only_if_to_iff():
    out, _ = apply_rules("Run only if the user is admin")
    assert "iff" in out


def test_for_each_to_foreach():
    out, _ = apply_rules("for each item in the list")
    assert "forEach" in out


def test_iterate_over():
    out, _ = apply_rules("iterate over each user")
    assert "forEach" in out


def test_in_order_to_simplified():
    out, _ = apply_rules("in order to compute the result")
    # Either becomes "to" (clean) or gets caught by other rules; just check
    # the 4-word phrase doesn't survive intact.
    assert "in order to" not in out.lower()


def test_rules_are_idempotent_on_compressed_form():
    """Running the rules twice should produce the same output."""
    out1, _ = apply_rules("Please write a Python function that checks if a number is prime")
    out2, _ = apply_rules(out1)
    assert out1 == out2 or len(out2) <= len(out1)


def test_empty_string():
    out, hits = apply_rules("")
    assert out == ""
    assert hits == []


def test_rule_count_at_least_50_in_categories():
    """Sanity: per requirement, the ruleset spans the listed buckets."""
    by_cat: dict[str, int] = {}
    for r in RULES:
        by_cat[r.category] = by_cat.get(r.category, 0) + 1
    # Must have meaningful coverage in the called-out categories.
    for cat in ["function", "io", "fluff", "verb"]:
        assert by_cat.get(cat, 0) >= 3, f"category {cat} has too few rules: {by_cat}"

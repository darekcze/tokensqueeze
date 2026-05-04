"""Shorthand Natural-language Syntax (SNS) rewrite rules.

Ordered, regex-based rewrite rules that compress verbose natural-language prompts
into a denser shorthand that LLMs still understand. The engine is dependency-light
and exposes per-rule tracing for diff/explain UIs.

Rules are grouped by category and applied in order. Each rule has a stable id,
a category, a regex pattern, a replacement, and a short rationale. The engine
is case-insensitive for matching but preserves replacement casing as written.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Rule:
    id: str
    category: str
    pattern: str
    replacement: str
    rationale: str = ""
    flags: int = re.IGNORECASE
    _compiled: re.Pattern | None = field(default=None, repr=False, compare=False)

    def compile(self) -> re.Pattern:
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, self.flags)
        return self._compiled


@dataclass
class RuleHit:
    rule_id: str
    category: str
    before: str
    after: str
    span: tuple[int, int]


# ---------------------------------------------------------------------------
# Rule definitions. Order matters: earlier rules normalize phrases that later
# rules then collapse. Keep replacements unambiguous to LLMs (-> for "produces",
# ? for conditionals, & for "and", etc.).
# ---------------------------------------------------------------------------

RULES: list[Rule] = [
    # --- 0. High-priority idiom rules (match whole canonical templates) -------
    # These run first so that common short prompts collapse to their tightest form
    # before more general rules further break them apart.
    Rule("idiom.prime_check", "idiom",
         r"^\s*(?:please\s+)?(?:write|create|build|implement|make|generate|code)\s+(?:a|an|the)?\s*(?:python|js|javascript|typescript|go|rust|java|c\+\+|cpp|ruby)?\s*function\s+(?:that\s+|which\s+|to\s+)?(?:checks?|tells?|determines?)\s+(?:if\s+|whether\s+)?(?:a\s+|the\s+|an\s+|given\s+)?number\s+is\s+prime\.?\s*$",
         r"isPrime(n)",
         "Whole-prompt idiom: 'write a function that checks if a number is prime' -> 'isPrime(n)'"),
    Rule("idiom.palindrome_check", "idiom",
         r"^\s*(?:please\s+)?(?:write|create|build|implement|make|generate)\s+(?:a|an|the)?\s*(?:python|js|javascript|typescript|go|rust|java|c\+\+|cpp|ruby)?\s*function\s+(?:that\s+|which\s+|to\s+)?(?:checks?|tells?|determines?)\s+(?:if\s+|whether\s+)?(?:a\s+|the\s+)?(?:string|word)\s+is\s+(?:a\s+)?palindrome\.?\s*$",
         r"isPalindrome(s)",
         "Whole-prompt idiom: palindrome check -> 'isPalindrome(s)'"),
    Rule("idiom.reverse_string", "idiom",
         r"^\s*(?:please\s+)?(?:write|create|build|implement)\s+(?:a|an|the)?\s*(?:python|js|javascript|typescript)?\s*function\s+(?:that\s+|to\s+)?reverses?\s+(?:a\s+)?string\.?\s*$",
         r"reverse(s)",
         "Whole-prompt idiom: reverse a string -> 'reverse(s)'"),
    Rule("idiom.fibonacci", "idiom",
         r"^\s*(?:please\s+)?(?:write|create|build|implement|generate)\s+(?:a|an|the)?\s*(?:python|js|javascript|typescript)?\s*function\s+(?:that\s+|to\s+)?(?:returns?|generates?|computes?|calculates?)\s+(?:the\s+)?(?:n[a-z-]*\s+)?fibonacci(?:\s+number|\s+sequence)?\.?\s*$",
         r"fib(n)",
         "Whole-prompt idiom: fibonacci -> 'fib(n)'"),
    Rule("idiom.factorial", "idiom",
         r"^\s*(?:please\s+)?(?:write|create|build|implement)\s+(?:a|an|the)?\s*(?:python|js|javascript|typescript)?\s*function\s+(?:that\s+|to\s+)?(?:returns?|computes?|calculates?)\s+(?:the\s+)?factorial\s+(?:of\s+(?:a\s+)?n(?:umber)?)?\.?\s*$",
         r"factorial(n)",
         "Whole-prompt idiom: factorial -> 'factorial(n)'"),

    # --- 1. Function/definition templates -------------------------------------
    Rule("fn.write_function_typed", "function",
         r"\b(?:write|create|build|implement|make|generate|develop|code)\s+(?:a|an|the)?\s*(python|js|javascript|typescript|ts|go|rust|java|c\+\+|cpp|c#|csharp|ruby|php|bash|shell)\s+function\s+(?:that\s+|which\s+|to\s+)?",
         r"fn[\1]:",
         "Compress 'write a python function that ...' to 'fn[python]:...'"),
    Rule("fn.write_function", "function",
         r"\b(?:write|create|build|implement|make|generate|develop|code)\s+(?:a|an|the)?\s*function\s+(?:that\s+|which\s+|to\s+)?",
         r"fn:",
         "Compress 'write a function that ...' to 'fn:...'"),
    Rule("fn.define_function", "function",
         r"\b(define|declare)\s+(?:a|an|the)?\s*function\s+(?:that\s+|which\s+|to\s+)?",
         r"fn: ",
         "Compress 'define a function that ...' to 'fn: ...'"),
    Rule("fn.write_program", "function",
         r"\b(write|create|build)\s+(?:a|an|the)?\s*(python|js|javascript|typescript|go|rust|java|bash|shell)?\s*(program|script|app|application)\s+(?:that\s+|which\s+|to\s+)?",
         r"prog(\2): ",
         "Compress 'write a python program that ...' to 'prog(python): ...'"),
    Rule("fn.write_class", "function",
         r"\b(write|create|implement|define)\s+(?:a|an|the)?\s*(python|js|typescript|java|c\+\+|ruby)?\s*class\s+(?:that\s+|which\s+|to\s+)?",
         r"cls(\2): ",
         "Compress 'create a class that ...' to 'cls: ...'"),
    Rule("fn.write_method", "function",
         r"\b(write|create|implement|add)\s+(?:a|an|the)?\s*method\s+(?:that\s+|which\s+|to\s+)?",
         r"method: ",
         "Compress 'write a method that ...' to 'method: ...'"),
    Rule("fn.write_endpoint", "function",
         r"\b(write|create|build|implement|expose)\s+(?:a|an|the)?\s*(rest|http|api|graphql)?\s*endpoint\s+(?:that\s+|which\s+|to\s+)?",
         r"endpoint(\2): ",
         "Compress 'create a REST endpoint that ...' to 'endpoint(rest): ...'"),
    Rule("fn.write_test", "function",
         r"\b(write|add|create)\s+(?:a|an|the|some)?\s*(unit|integration|e2e)?\s*tests?\s+(?:that\s+|which\s+|to\s+|for\s+)?",
         r"tests(\2): ",
         "Compress 'write unit tests that ...' to 'tests(unit): ...'"),

    # --- 1b. JSON-first capture (must run before io.returns_a) ---------------
    Rule("json.early.return_as_json", "json",
         r"\breturns?\s+(?:the\s+)?(?:result\s+|response\s+|output\s+)?(?:as|in|using)\s+json(?:\s+format)?\b",
         r"->json",
         "Early capture: 'return the result as JSON' -> '->json'"),
    Rule("json.early.respond_in_json", "json",
         r"\b(respond|reply|answer)\s+(?:in|with|using)\s+json(?:\s+format)?",
         r"->json",
         "Early capture: 'respond in JSON' -> '->json'"),
    Rule("json.early.output_format", "json",
         r"\boutput\s+(?:the\s+)?(?:result\s+)?(?:in|as|using)\s+(json|xml|yaml|csv|markdown|md)\s+format",
         r"->\1",
         "Early capture: 'output in <fmt> format' -> '-><fmt>'"),
    Rule("json.early.format_as", "json",
         r"\bformat\s+(?:the\s+)?(?:output\s+|response\s+)?as\s+(json|xml|yaml|csv|markdown|md)",
         r"->\1",
         "Early capture: 'format the output as <fmt>' -> '-><fmt>'"),

    # --- 2. Data flow / I/O ---------------------------------------------------
    Rule("io.takes_returns", "io",
         r"\bthat\s+takes\s+(.+?)\s+(?:and|,)\s+returns\s+",
         r"(\1) -> ",
         "Compress 'that takes X and returns ...' to '(X) -> ...'"),
    Rule("io.takes_only", "io",
         r"\bthat\s+takes\s+(?:in\s+)?(?:a|an|the)?\s*",
         r"(",
         "Compress 'that takes a ...' opening to '('"),
    Rule("io.given_input", "io",
         r"\bgiven\s+(?:a|an|the)?\s*(.+?)\s+as\s+input\s*,?\s*",
         r"in=\1; ",
         "Compress 'given X as input,' to 'in=X;'"),
    Rule("io.accepts_arg", "io",
         r"\baccepts?\s+(?:a|an|the)?\s*",
         r"in: ",
         "Compress 'accepts a ...' to 'in: ...'"),
    Rule("io.returns_a", "io",
         r"\breturns?\s+(?:a|an|the)?\s*",
         r"-> ",
         "Compress 'returns a ...' to '-> ...'"),
    Rule("io.outputs_a", "io",
         r"\boutputs?\s+(?:a|an|the)?\s*",
         r"out: ",
         "Compress 'outputs a ...' to 'out: ...'"),
    Rule("io.print_the", "io",
         r"\bprints?\s+(?:out\s+)?(?:the|a|an)?\s*",
         r"print: ",
         "Compress 'prints out the ...' to 'print: ...'"),

    # --- 3. Conditionals ------------------------------------------------------
    Rule("if.if_then", "conditional",
         r"\bif\s+(.+?)\s+then\s+",
         r"if(\1)? ",
         "Compress 'if X then ...' to 'if(X)? ...'"),
    Rule("if.when_x", "conditional",
         r"\bwhen\s+(.+?)\s*,\s*",
         r"on(\1): ",
         "Compress 'when X,' to 'on(X):'"),
    Rule("if.in_case", "conditional",
         r"\bin\s+case\s+(?:of|that)?\s*",
         r"if: ",
         "Compress 'in case of/that' to 'if:'"),
    Rule("if.otherwise", "conditional",
         r"\botherwise\s*,?\s*",
         r"else: ",
         "Compress 'otherwise,' to 'else:'"),
    Rule("if.unless", "conditional",
         r"\bunless\s+",
         r"if !",
         "Compress 'unless' to 'if !'"),
    Rule("if.only_if", "conditional",
         r"\bonly\s+if\s+",
         r"iff ",
         "Compress 'only if' to 'iff'"),

    # --- 4. List operations ---------------------------------------------------
    Rule("list.iterate_over", "list",
         r"\b(iterate|loop|go)\s+(?:over|through)\s+(?:each|every|all)?\s*",
         r"forEach ",
         "Compress 'iterate over each ...' to 'forEach ...'"),
    Rule("list.for_each", "list",
         r"\bfor\s+each\s+",
         r"forEach ",
         "Compress 'for each' to 'forEach'"),
    Rule("list.list_of", "list",
         r"\b(?:a\s+)?list\s+of\s+",
         r"[",
         "Compress 'a list of' to '['"),
    Rule("list.array_of", "list",
         r"\b(?:an\s+)?array\s+of\s+",
         r"[",
         "Compress 'an array of' to '['"),
    Rule("list.sort_by", "list",
         r"\bsort(?:ed)?\s+by\s+",
         r"sortBy: ",
         "Compress 'sorted by' to 'sortBy:'"),
    Rule("list.filter_where", "list",
         r"\bfilter(?:ed)?\s+(?:by|where|to\s+only\s+include)\s+",
         r"filter: ",
         "Compress 'filter by' to 'filter:'"),
    Rule("list.map_each", "list",
         r"\bmap\s+(?:each\s+)?(?:item|element)?\s*to\s+",
         r"map: ",
         "Compress 'map each item to' to 'map:'"),
    Rule("list.group_by", "list",
         r"\bgroup(?:ed)?\s+by\s+",
         r"groupBy: ",
         "Compress 'grouped by' to 'groupBy:'"),

    # --- 5. JSON / structured output -----------------------------------------
    Rule("json.return_json", "json",
         r"\breturns?\s+(?:the\s+)?(?:result\s+|response\s+|output\s+)?(?:as|in|using)?\s*json(?:\s+format)?\b",
         r"->json",
         "Compress 'return the result as JSON' to '->json'"),
    Rule("json.respond_in_json", "json",
         r"\b(respond|reply|answer)\s+(?:in|with|using)\s+json(?:\s+format)?",
         r"->json",
         "Compress 'respond in JSON format' to '->json'"),
    Rule("json.output_format", "json",
         r"\boutput\s+(?:the\s+)?(?:result\s+)?(?:in|as|using)\s+(json|xml|yaml|csv|markdown|md)\s+format",
         r"->\1",
         "Compress 'output in JSON format' to '->json'"),
    Rule("json.format_as", "json",
         r"\bformat\s+(?:the\s+)?(?:output\s+|response\s+)?as\s+(json|xml|yaml|csv|markdown|md)",
         r"->\1",
         "Compress 'format the output as JSON' to '->json'"),
    Rule("json.json_array", "json",
         r"\bjson\s+array\s+of\s+",
         r"json[",
         "Compress 'JSON array of' to 'json['"),
    Rule("json.with_fields", "json",
         r"\bwith\s+(?:the\s+)?fields?\s+",
         r" {",
         "Compress 'with the fields' to ' {'"),
    Rule("json.with_keys", "json",
         r"\bwith\s+(?:the\s+)?keys?\s+",
         r" {",
         "Compress 'with the keys' to ' {'"),

    # --- 6. Fluff / filler removal -------------------------------------------
    Rule("fluff.please", "fluff",
         r"\bplease\s+",
         r"",
         "Drop 'please'"),
    Rule("fluff.kindly", "fluff",
         r"\bkindly\s+",
         r"",
         "Drop 'kindly'"),
    Rule("fluff.could_you", "fluff",
         r"\b(?:could|can|would|will)\s+you\s+(?:please\s+)?",
         r"",
         "Drop 'could you / can you / would you please'"),
    Rule("fluff.i_would_like", "fluff",
         r"\bi\s+(?:would\s+like|want|need)\s+(?:you\s+)?to\s+",
         r"",
         "Drop 'I would like you to'"),
    Rule("fluff.help_me", "fluff",
         r"\bhelp\s+me\s+(?:to\s+)?",
         r"",
         "Drop 'help me to'"),
    Rule("fluff.in_order_to", "fluff",
         r"\bin\s+order\s+to\b",
         r"to",
         "Replace 'in order to' with 'to'"),
    Rule("fluff.due_to_fact", "fluff",
         r"\bdue\s+to\s+the\s+fact\s+that\b",
         r"because",
         "Replace 'due to the fact that' with 'because'"),
    Rule("fluff.at_this_point", "fluff",
         r"\bat\s+this\s+point\s+in\s+time\b",
         r"now",
         "Replace 'at this point in time' with 'now'"),
    Rule("fluff.it_is_important", "fluff",
         r"\bit\s+is\s+(?:important|crucial|essential|necessary|vital)\s+(?:to\s+note\s+)?that\s+",
         r"",
         "Drop 'it is important to note that'"),
    Rule("fluff.as_a_matter", "fluff",
         r"\bas\s+a\s+matter\s+of\s+fact\s*,?\s*",
         r"",
         "Drop 'as a matter of fact'"),
    Rule("fluff.needless_to_say", "fluff",
         r"\bneedless\s+to\s+say\s*,?\s*",
         r"",
         "Drop 'needless to say'"),
    Rule("fluff.in_my_opinion", "fluff",
         r"\bin\s+my\s+(?:opinion|view)\s*,?\s*",
         r"",
         "Drop 'in my opinion'"),
    Rule("fluff.thanks", "fluff",
         r"\b(?:thanks?|thank\s+you)(?:\s+(?:so|very)\s+much)?\s*[!.]*\s*$",
         r"",
         "Drop trailing 'thank you'"),
    Rule("fluff.basically", "fluff",
         r"\b(basically|essentially|literally|actually|really|just)\s+",
         r"",
         "Drop hedge adverbs"),
    Rule("fluff.very", "fluff",
         r"\b(very|quite|rather|somewhat|fairly)\s+",
         r"",
         "Drop intensifiers"),
    Rule("fluff.you_should", "fluff",
         r"\byou\s+should\s+(?:probably\s+)?",
         r"",
         "Drop 'you should'"),
    Rule("fluff.make_sure", "fluff",
         r"\bmake\s+sure\s+(?:to\s+|that\s+)?",
         r"must ",
         "Replace 'make sure to' with 'must'"),
    Rule("fluff.be_sure", "fluff",
         r"\bbe\s+sure\s+to\s+",
         r"must ",
         "Replace 'be sure to' with 'must'"),
    Rule("fluff.dont_forget", "fluff",
         r"\bdon'?t\s+forget\s+to\s+",
         r"must ",
         "Replace 'do not forget to' with 'must'"),
    Rule("fluff.try_to", "fluff",
         r"\btry\s+to\s+",
         r"",
         "Drop 'try to'"),
    Rule("fluff.go_ahead", "fluff",
         r"\bgo\s+ahead\s+and\s+",
         r"",
         "Drop 'go ahead and'"),

    # --- 6b. Predicate / "X is Y" shortening (must run before fluff to catch "a") ---
    Rule("pred.checks_if", "predicate",
         r"\bchecks?\s+(?:if|whether)\s+",
         r"? ",
         "Compress 'checks if X' to '? X'"),
    Rule("pred.tells_if", "predicate",
         r"\btells?\s+(?:if|whether)\s+",
         r"? ",
         "Compress 'tells whether X' to '? X'"),
    Rule("pred.determines_if", "predicate",
         r"\bdetermines?\s+(?:if|whether)\s+",
         r"? ",
         "Compress 'determines whether X' to '? X'"),
    Rule("pred.is_prime", "predicate",
         r"\b(?:a\s+)?(?:given\s+)?number\s+is\s+prime\b",
         r"isPrime(n)",
         "Compress 'a number is prime' to 'isPrime(n)'"),
    Rule("pred.is_palindrome", "predicate",
         r"\b(?:a\s+)?(?:given\s+)?(?:string|word)\s+is\s+(?:a\s+)?palindrome\b",
         r"isPalindrome(s)",
         "Compress 'a string is a palindrome' to 'isPalindrome(s)'"),
    Rule("pred.is_even_odd", "predicate",
         r"\b(?:a\s+)?(?:given\s+)?number\s+is\s+(even|odd)\b",
         r"is\1(n)",
         "Compress 'a number is even/odd' to 'isEven(n)' / 'isOdd(n)'"),
    Rule("pred.given_a", "predicate",
         r"\bgiven\s+(?:a|an|the)\s+",
         r"given ",
         "Drop article after 'given'"),

    # --- 7. Verb shortening ---------------------------------------------------
    Rule("verb.utilize", "verb",
         r"\butilize\b",
         r"use",
         "Replace 'utilize' with 'use'"),
    Rule("verb.demonstrate", "verb",
         r"\bdemonstrate\b",
         r"show",
         "Replace 'demonstrate' with 'show'"),
    Rule("verb.facilitate", "verb",
         r"\bfacilitate\b",
         r"help",
         "Replace 'facilitate' with 'help'"),
    Rule("verb.implement", "verb",
         r"\bimplement\b",
         r"impl",
         "Abbreviate 'implement' to 'impl'"),
    Rule("verb.calculate", "verb",
         r"\bcalculate\b",
         r"calc",
         "Abbreviate 'calculate' to 'calc'"),
    Rule("verb.generate", "verb",
         r"\bgenerate\b",
         r"gen",
         "Abbreviate 'generate' to 'gen'"),
    Rule("verb.determine", "verb",
         r"\bdetermine\b",
         r"find",
         "Replace 'determine' with 'find'"),
    Rule("verb.investigate", "verb",
         r"\binvestigate\b",
         r"check",
         "Replace 'investigate' with 'check'"),
    Rule("verb.analyze", "verb",
         r"\banalyze\b",
         r"analyse",
         "Normalize 'analyze' (slightly shorter form)"),
    Rule("verb.transform", "verb",
         r"\btransform\b",
         r"map",
         "Replace 'transform' with 'map'"),
    Rule("verb.ensure_that", "verb",
         r"\bensure\s+that\b",
         r"ensure",
         "Drop 'that' after 'ensure'"),

    # --- 8. Polish (PL) common prompt forms ----------------------------------
    Rule("pl.napisz_funkcje", "polish",
         r"\bnapisz\s+(?:funkcj[ęe])\s+(?:która|kt[oó]ra)\s+",
         r"fn: ",
         "Polish: 'napisz funkcję która ...' -> 'fn: ...'"),
    Rule("pl.stworz_program", "polish",
         r"\b(?:stw[oó]rz|napisz|zr[oó]b)\s+program\s+(?:kt[oó]ry|do)\s+",
         r"prog: ",
         "Polish: 'stwórz program który ...' -> 'prog: ...'"),
    Rule("pl.prosze", "polish",
         r"\b(?:prosz[ęe]|prosil[ae]m)\s+",
         r"",
         "Polish: drop 'proszę'"),
    Rule("pl.czy_mozesz", "polish",
         r"\bczy\s+mo[żz]esz\s+",
         r"",
         "Polish: drop 'czy możesz'"),
    Rule("pl.zwroc", "polish",
         r"\b(?:zwr[oó][ćc]|zwraca|zwracaj[ąa]ca?|zwracaj[ąa]cy)\s+",
         r"-> ",
         "Polish: 'zwróć/zwraca/zwracająca' -> '->'"),
    Rule("pl.wypisz", "polish",
         r"\bwypisz\s+",
         r"print: ",
         "Polish: 'wypisz' -> 'print:'"),
    Rule("pl.dla_kazdego", "polish",
         r"\bdla\s+ka[żz]dego\s+",
         r"forEach ",
         "Polish: 'dla każdego' -> 'forEach'"),
    Rule("pl.jezeli", "polish",
         r"\b(?:je[żz]eli|je[śs]li)\s+",
         r"if ",
         "Polish: 'jeżeli/jeśli' -> 'if'"),

    # --- 9. Compact Chinese (ZH) prompt forms --------------------------------
    Rule("zh.write_function", "chinese",
         r"(?:请)?写(?:一个)?(?:函数|方法)(?:用于|来|，)?",
         r"fn: ",
         "Chinese: '写一个函数' -> 'fn:'"),
    Rule("zh.return", "chinese",
         r"返回(?:一个)?",
         r"-> ",
         "Chinese: '返回' -> '->'"),
    Rule("zh.if", "chinese",
         r"如果",
         r"if ",
         "Chinese: '如果' -> 'if'"),
    Rule("zh.please", "chinese",
         r"请",
         r"",
         "Chinese: drop '请'"),

    # --- 10. Whitespace / final tidy ----------------------------------------
    Rule("tidy.multi_space", "tidy",
         r"[ \t]{2,}",
         r" ",
         "Collapse runs of whitespace"),
    Rule("tidy.space_punct", "tidy",
         r"\s+([,.;:?])",
         r"\1",
         "Drop space before punctuation (excluding '!' which is a logical-not in SNS)"),
    Rule("tidy.repeat_punct", "tidy",
         r"([.!?]){2,}",
         r"\1",
         "Collapse repeated punctuation"),
    Rule("tidy.trim", "tidy",
         r"^\s+|\s+$",
         r"",
         "Trim leading/trailing whitespace"),
]


def all_rules() -> list[Rule]:
    """Return the master list of rules in application order."""
    return RULES


def apply_rules(
    text: str,
    rules: Iterable[Rule] | None = None,
    *,
    trace: bool = False,
) -> tuple[str, list[RuleHit]]:
    """Apply rules in order. Returns (compressed_text, hits).

    `hits` contains one RuleHit per match, in the order matches were applied,
    with the original snippet, the replacement, and the span where the match
    was found in the input *as it stood at that step*.
    """
    rules = list(rules) if rules is not None else RULES
    hits: list[RuleHit] = []
    out = text

    for rule in rules:
        pat = rule.compile()
        if trace:
            new_chunks: list[str] = []
            last = 0
            mutated = False
            for m in pat.finditer(out):
                before_snippet = m.group(0)
                replacement = m.expand(rule.replacement)
                hits.append(RuleHit(
                    rule_id=rule.id,
                    category=rule.category,
                    before=before_snippet,
                    after=replacement,
                    span=m.span(),
                ))
                new_chunks.append(out[last:m.start()])
                new_chunks.append(replacement)
                last = m.end()
                mutated = True
            if mutated:
                new_chunks.append(out[last:])
                out = "".join(new_chunks)
        else:
            new_out, n = pat.subn(rule.replacement, out)
            if n:
                hits.append(RuleHit(rule.id, rule.category, "", "", (-1, -1)))
            out = new_out

    return out, hits


def explain(text: str) -> dict:
    """Return a structured explanation of which rules fired on `text`."""
    compressed, hits = apply_rules(text, trace=True)
    return {
        "input": text,
        "output": compressed,
        "rules_applied": [
            {
                "id": h.rule_id,
                "category": h.category,
                "before": h.before,
                "after": h.after,
                "span": list(h.span),
            }
            for h in hits
        ],
        "rule_count": len(hits),
    }

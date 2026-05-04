"""Command-line entry point: `squeeze`.

    echo "Write a python function that ..." | squeeze
    squeeze --strategy sns --explain "compress me"
    squeeze --json --encoding cl100k_base "..."

Reads from stdin if no positional prompt is given.
"""
from __future__ import annotations

import argparse
import json
import sys

from .compress import compress_detailed
from .tokenizers import count_tokens


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return " ".join(args.prompt)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("No prompt provided. Pipe via stdin or pass as argument.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="squeeze",
        description="TokenSqueeze CLI — compress prompts for LLMs.",
    )
    p.add_argument("prompt", nargs="*", help="Prompt text (omit to read stdin).")
    p.add_argument(
        "--strategy", "-s",
        choices=["auto", "sns", "llmlingua2", "gist"],
        default="auto",
        help="Compression strategy (default: auto).",
    )
    p.add_argument(
        "--encoding", "-e",
        default="cl100k_base",
        help="tiktoken encoding for token counts (default: cl100k_base).",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Emit a JSON record instead of plain text.",
    )
    p.add_argument(
        "--explain", action="store_true",
        help="Print the list of rules that fired (and the diff) to stderr.",
    )
    p.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress savings line on stderr.",
    )
    p.add_argument(
        "--version", action="version", version="tokensqueeze 0.1.0",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    prompt = _read_prompt(args)

    result = compress_detailed(prompt, strategy=args.strategy)

    # Recount tokens with the user-requested encoding (compress_detailed used default).
    o = count_tokens(result.original, args.encoding)
    c = count_tokens(result.compressed, args.encoding)
    saved = o - c
    reduction = (saved / o) if o else 0.0

    if args.json:
        payload = {
            "original": result.original,
            "compressed": result.compressed,
            "strategy": result.strategy,
            "classified_as": result.classified_as,
            "warning": result.warning,
            "tokens": {
                "encoding": args.encoding,
                "original": o,
                "compressed": c,
                "saved": saved,
                "reduction": round(reduction, 4),
            },
            "rules_applied": result.rules_applied,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(result.compressed)
        if not result.compressed.endswith("\n"):
            sys.stdout.write("\n")

    if args.explain and not args.json:
        sys.stderr.write("\n--- rules applied ---\n")
        for r in result.rules_applied:
            sys.stderr.write(f"[{r['category']}] {r['id']}: {r['before']!r} -> {r['after']!r}\n")
        if result.warning:
            sys.stderr.write(f"\nwarning: {result.warning}\n")

    if not args.quiet and not args.json:
        pct = round(reduction * 100, 1)
        sys.stderr.write(
            f"[squeeze] {o} -> {c} tokens ({args.encoding}, -{pct}%) strategy={result.strategy}\n"
        )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

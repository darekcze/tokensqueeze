"""Fidelity validation harness.

Given a list of prompts, compress each, then score how close the compressed
prompt is to the original. Two scoring modes:

  1. Local: sentence-transformers cosine similarity (preferred), falling back
     to difflib.SequenceMatcher if the optional dep is missing.
  2. LLM-as-judge (optional hook): set TOKENSQUEEZE_LLM_JUDGE=1 and provide a
     `judge_fn` to `run()` to score each pair via your favourite model.

Inputs:
  - JSONL: one object per line with a `prompt` field (and optional `id`).
  - CSV:   one column named `prompt` (or first column).
  - HuggingFace `datasets` HumanEval (optional): set --humaneval to load it.

Outputs:
  - Prints a summary table.
  - With --report-json, writes a structured JSON report.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import statistics
import sys
from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Iterator

from tokensqueeze import compress, count_tokens
from tokensqueeze.compress import compress_detailed


@dataclass
class PairResult:
    id: str
    original: str
    compressed: str
    strategy: str
    similarity: float
    similarity_method: str
    tokens_original: int
    tokens_compressed: int
    reduction: float
    judge_score: float | None = None


# ---------------------------------------------------------------------------
# Similarity backends
# ---------------------------------------------------------------------------

def _try_load_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer, util  # type: ignore
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return model, util
    except Exception:
        return None, None


def _difflib_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _make_similarity_fn() -> tuple[Callable[[str, str], float], str]:
    model, util = _try_load_sentence_transformer()
    if model is None:
        return _difflib_similarity, "difflib"

    def st_sim(a: str, b: str) -> float:
        ea = model.encode(a, convert_to_tensor=True)
        eb = model.encode(b, convert_to_tensor=True)
        return float(util.cos_sim(ea, eb)[0][0])

    return st_sim, "sentence-transformers"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _iter_jsonl(path: str) -> Iterator[dict]:
    with open(path) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row.setdefault("id", str(i))
            yield row


def _iter_csv(path: str) -> Iterator[dict]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return
        prompt_col = "prompt" if "prompt" in reader.fieldnames else reader.fieldnames[0]
        for i, row in enumerate(reader):
            yield {"id": row.get("id", str(i)), "prompt": row[prompt_col]}


def _iter_humaneval() -> Iterator[dict]:
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        raise SystemExit(
            "HumanEval requires `datasets`. Install with `pip install datasets`."
        )
    ds = load_dataset("openai_humaneval", split="test")
    for i, row in enumerate(ds):
        yield {"id": row.get("task_id", str(i)), "prompt": row["prompt"]}


def _load(args: argparse.Namespace) -> Iterable[dict]:
    if args.humaneval:
        return _iter_humaneval()
    if not args.input:
        raise SystemExit("Provide --input PATH (.jsonl or .csv) or --humaneval.")
    if args.input.endswith(".jsonl"):
        return _iter_jsonl(args.input)
    if args.input.endswith(".csv"):
        return _iter_csv(args.input)
    raise SystemExit(f"Unsupported input format: {args.input}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(
    rows: Iterable[dict],
    strategy: str = "auto",
    judge_fn: Callable[[str, str], float] | None = None,
) -> list[PairResult]:
    sim_fn, sim_name = _make_similarity_fn()
    judge_enabled = os.environ.get("TOKENSQUEEZE_LLM_JUDGE") == "1" and judge_fn is not None

    results: list[PairResult] = []
    for row in rows:
        prompt = row["prompt"]
        det = compress_detailed(prompt, strategy=strategy)
        sim = sim_fn(prompt, det.compressed) if prompt else 1.0
        o = count_tokens(prompt)
        c = count_tokens(det.compressed)
        results.append(PairResult(
            id=str(row.get("id", "")),
            original=prompt,
            compressed=det.compressed,
            strategy=det.strategy,
            similarity=round(sim, 4),
            similarity_method=sim_name,
            tokens_original=o,
            tokens_compressed=c,
            reduction=round((o - c) / o, 4) if o else 0.0,
            judge_score=judge_fn(prompt, det.compressed) if judge_enabled else None,
        ))
    return results


def summarize(results: list[PairResult]) -> dict:
    if not results:
        return {"count": 0}
    sims = [r.similarity for r in results]
    reds = [r.reduction for r in results]
    return {
        "count": len(results),
        "similarity_mean": round(statistics.mean(sims), 4),
        "similarity_min": round(min(sims), 4),
        "similarity_p10": round(sorted(sims)[len(sims) // 10], 4) if len(sims) >= 10 else round(min(sims), 4),
        "reduction_mean": round(statistics.mean(reds), 4),
        "reduction_max": round(max(reds), 4),
        "tokens_saved_total": sum(r.tokens_original - r.tokens_compressed for r in results),
        "similarity_method": results[0].similarity_method,
    }


def print_report(results: list[PairResult], summary: dict) -> None:
    print("=" * 72)
    print(f"TokenSqueeze fidelity report — {summary.get('count', 0)} prompts")
    print(f"Similarity method : {summary.get('similarity_method')}")
    print(f"Mean similarity   : {summary.get('similarity_mean')}")
    print(f"Min similarity    : {summary.get('similarity_min')}")
    print(f"P10 similarity    : {summary.get('similarity_p10')}")
    print(f"Mean reduction    : {summary.get('reduction_mean')}")
    print(f"Max reduction     : {summary.get('reduction_max')}")
    print(f"Total tokens saved: {summary.get('tokens_saved_total')}")
    print("=" * 72)
    # Show the 5 worst-fidelity rows for inspection.
    worst = sorted(results, key=lambda r: r.similarity)[:5]
    if worst:
        print("\nWorst-fidelity samples:")
        for r in worst:
            print(f"  [{r.id}] sim={r.similarity:.3f} red={r.reduction:.2%}")
            print(f"    in : {r.original[:100]!r}")
            print(f"    out: {r.compressed[:100]!r}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TokenSqueeze fidelity validator.")
    p.add_argument("--input", help="Path to .jsonl or .csv with a `prompt` field.")
    p.add_argument("--humaneval", action="store_true", help="Load OpenAI HumanEval via datasets.")
    p.add_argument("--strategy", default="auto", choices=["auto", "sns", "llmlingua2", "gist"])
    p.add_argument("--report-json", help="Write a JSON report to this path.")
    p.add_argument("--limit", type=int, default=0, help="Process at most N prompts (0 = no limit).")
    args = p.parse_args(argv)

    rows = list(_load(args))
    if args.limit:
        rows = rows[: args.limit]

    results = run(rows, strategy=args.strategy)
    summary = summarize(results)
    print_report(results, summary)

    if args.report_json:
        with open(args.report_json, "w") as f:
            json.dump({"summary": summary, "results": [asdict(r) for r in results]}, f, indent=2)
        print(f"\nWrote {args.report_json}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

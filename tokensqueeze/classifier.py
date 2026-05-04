"""Lightweight prompt-type classifier.

Default path is a bundled JSON heuristic model — keyword counts per class,
with class priors. If the user has scikit-learn and sentence-transformers
installed and a pickled `classifier.pkl` next to this file, we use that
instead.

Classes: code | reasoning | qa | creative
"""
from __future__ import annotations

import json
import os
import pickle
import re
from dataclasses import dataclass
from typing import Iterable

_DIR = os.path.dirname(os.path.abspath(__file__))
_MODEL_JSON = os.path.join(_DIR, "classifier_model.json")
_MODEL_PICKLE = os.path.join(_DIR, "classifier.pkl")


CLASSES = ("code", "reasoning", "qa", "creative")

# Bundled heuristic model. Each class has positive keywords/regex hints.
DEFAULT_MODEL: dict = {
    "version": 1,
    "classes": list(CLASSES),
    "priors": {"code": 0.3, "reasoning": 0.2, "qa": 0.3, "creative": 0.2},
    "keywords": {
        "code": [
            "function", "class", "method", "script", "program", "code", "api",
            "endpoint", "json", "regex", "python", "javascript", "typescript",
            "sql", "bash", "shell", "rust", "go", "java", "c++", "c#",
            "compile", "debug", "refactor", "implement", "unit test", "test",
            "algorithm", "data structure", "import", "def ", "return ",
            "{", "}", "()", "->", "=>", "==", "!=", "fn:", "fn(",
        ],
        "reasoning": [
            "explain", "why", "prove", "step by step", "reason", "think",
            "derive", "analy", "compare", "contrast", "trade-off", "tradeoff",
            "evaluate", "argue", "logic", "implication", "deduce", "infer",
            "conclude", "because", "therefore", "however", "if and only if",
        ],
        "qa": [
            "what is", "what's", "who is", "who's", "where is", "when did",
            "when was", "how many", "how much", "which", "define", "definition",
            "summary", "summarize", "tldr", "tl;dr", "?",
        ],
        "creative": [
            "write a story", "poem", "haiku", "novel", "character", "plot",
            "dialogue", "narrative", "lyric", "song", "screenplay", "tagline",
            "slogan", "advertisement", "marketing copy", "creative", "imagine",
            "fictional", "fantasy", "sci-fi", "fairy tale",
        ],
    },
}


@dataclass
class Prediction:
    label: str
    score: float
    scores: dict


def _ensure_model():
    if not os.path.exists(_MODEL_JSON):
        with open(_MODEL_JSON, "w") as f:
            json.dump(DEFAULT_MODEL, f, indent=2)
    with open(_MODEL_JSON) as f:
        return json.load(f)


def _heuristic_predict(text: str, model: dict) -> Prediction:
    t = text.lower()
    scores: dict[str, float] = {c: 0.0 for c in model["classes"]}
    for cls, kws in model["keywords"].items():
        for kw in kws:
            # Regex-escape; use word boundary unless the keyword has punctuation.
            if any(ch in kw for ch in "{}()->=!?+;:,/\\"):
                if kw in t:
                    scores[cls] += 1.0
            else:
                if re.search(r"\b" + re.escape(kw) + r"\b", t):
                    scores[cls] += 1.0
    # Add priors and normalize.
    for cls in scores:
        scores[cls] += float(model["priors"].get(cls, 0.0))
    total = sum(scores.values()) or 1.0
    norm = {k: v / total for k, v in scores.items()}
    label = max(norm, key=norm.get)
    return Prediction(label=label, score=norm[label], scores=norm)


def _try_pickle_predict(text: str) -> Prediction | None:
    if not os.path.exists(_MODEL_PICKLE):
        return None
    try:
        with open(_MODEL_PICKLE, "rb") as f:
            bundle = pickle.load(f)
        # Bundle is expected to be: {"vectorizer": v, "model": m, "labels": [...]}
        v = bundle["vectorizer"]
        m = bundle["model"]
        labels = bundle["labels"]
        X = v.transform([text])
        if hasattr(m, "predict_proba"):
            probs = m.predict_proba(X)[0]
            scores = {labels[i]: float(probs[i]) for i in range(len(labels))}
        else:
            pred = m.predict(X)[0]
            scores = {label: (1.0 if label == pred else 0.0) for label in labels}
        label = max(scores, key=scores.get)
        return Prediction(label=label, score=scores[label], scores=scores)
    except Exception:
        return None


def predict(text: str) -> Prediction:
    """Predict prompt class. Tries pickle model, falls back to heuristic."""
    pred = _try_pickle_predict(text)
    if pred is not None:
        return pred
    model = _ensure_model()
    return _heuristic_predict(text, model)


def classify(text: str) -> str:
    """Convenience: return only the predicted label."""
    return predict(text).label


# ---------------------------------------------------------------------------
# Optional: train a real model when sklearn / sentence-transformers exist.
# Run as: python -m tokensqueeze.classifier train <jsonl_path>
# JSONL format: {"text": "...", "label": "code|reasoning|qa|creative"}
# ---------------------------------------------------------------------------
def train(jsonl_path: str, output_path: str = _MODEL_PICKLE) -> str:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except ImportError as e:
        raise SystemExit(
            "sklearn is required to train. Install with: pip install scikit-learn"
        ) from e

    texts: list[str] = []
    labels: list[str] = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            texts.append(row["text"])
            labels.append(row["label"])

    label_set = sorted(set(labels))
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vec.fit_transform(texts)
    model = LogisticRegression(max_iter=1000)
    model.fit(X, labels)

    with open(output_path, "wb") as f:
        pickle.dump({"vectorizer": vec, "model": model, "labels": label_set}, f)
    return output_path


def _cli(argv: Iterable[str]) -> int:
    args = list(argv)
    if not args:
        print("Usage: python -m tokensqueeze.classifier {predict|train} ...")
        return 2
    cmd = args[0]
    if cmd == "predict":
        text = " ".join(args[1:]) or input()
        p = predict(text)
        print(json.dumps({"label": p.label, "score": p.score, "scores": p.scores}, indent=2))
        return 0
    if cmd == "train":
        if len(args) < 2:
            print("train requires a JSONL path")
            return 2
        out = train(args[1])
        print(f"Saved model to {out}")
        return 0
    print(f"Unknown command: {cmd}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    import sys
    raise SystemExit(_cli(sys.argv[1:]))

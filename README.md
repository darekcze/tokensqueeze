# TokenSqueeze ⚡

**Hybrid prompt compression for LLMs — SNS shorthand, optional LLMLingua-2, adaptive strategy selection.**

`pip install tokensqueeze` · MIT · v0.1.0

TokenSqueeze compresses verbose natural-language prompts into a denser shorthand that LLMs still understand, reducing token usage and API cost. It combines three layers:

1. **SNS (Shorthand Natural-language Syntax)** — ~75 ordered regex rewrite rules that convert function templates, I/O descriptions, conditionals, list ops, and fluff into symbolic shorthand (`→`, `|`, `?:`, `{}`). Fast, deterministic, explainable.
2. **LLMLingua-2 bridge** (optional) — when the `llmlingua` package and model are installed, semantic pruning is preferred for reasoning and creative prompts.
3. **Adaptive orchestrator** — a lightweight heuristic classifier routes each prompt to the best strategy (`code` → SNS, `reasoning/creative` → LLMLingua-2 fallback to SNS).

A fourth layer, **gisting** (Mu et al., 2023), is documented and stubbed — it requires a fine-tuned model and is on the roadmap, not yet functional.

---

## Quick start

```bash
pip install tokensqueeze                              # core; zero hard deps
pip install "tokensqueeze[tokenizer,server]"          # add tiktoken + FastAPI

echo "Write a Python function that checks if a number is prime" | squeeze
# isPrime(n)
# [squeeze] 12 -> 4 tokens (cl100k_base, -66.7%) strategy=sns
```

**Python API:**

```python
from tokensqueeze import compress, explain

compressed = compress("Please write a function that returns the sum of an array")
# -> 'fn:-> sum of an array'

details = explain("Could you write a Python function that checks if a number is prime")
# details['output']        -> 'isPrime(n)'
# details['rules_applied'] -> list of rule traces
```

---

## Implementation status

| Component | Status | Notes |
| :--- | :--- | :--- |
| SNS rules engine | ✅ Implemented | ~75 rules across 10 categories; EN/PL/ZH |
| Adaptive classifier | ✅ Implemented | Heuristic JSON model bundled; swap in a trained pickle |
| LLMLingua-2 bridge | ✅ Implemented | Optional dep; falls back to SNS with a warning if absent |
| CLI (`squeeze`) | ✅ Implemented | stdin/arg, `--json`, `--explain`, `--strategy` |
| FastAPI server | ✅ Implemented | `POST /compress`, `GET /health`, `GET /stats` |
| VS Code extension | ✅ Source complete | Build with `npm run compile`; not yet on VS Code Marketplace |
| Browser extension (MV3) | ✅ Source complete | Load unpacked in Chrome/Firefox; not yet on stores |
| OpenClaw preprocessor | ✅ Implemented | Shell script + env-var config |
| Fidelity validation harness | ✅ Implemented | difflib + optional sentence-transformers |
| Gisting module | 🗺 Roadmap | Stub documented; requires a fine-tuned LM (Mu et al., 2023) |
| Trained classifier (sklearn) | 🗺 Roadmap | Training script present; no bundled training data yet |

---

## How it works

```
              ┌──────────────────────┐
prompt ──────▶│ classifier (heuristic│──┐  routes by prompt type
              └──────────────────────┘  │
                                        ▼
                            ┌─────────────────────┐
                            │  SNS rules engine   │─► compressed prompt
                            └─────────────────────┘
                                        ▲
                            ┌─────────────────────┐ (optional)
                            │  LLMLingua-2 bridge │
                            └─────────────────────┘
```

- **SNS** is ~75 ordered regex rewrite rules covering function templates, I/O,
  conditionals, list ops, JSON output, fluff removal, verb shortening, Polish,
  and Chinese forms. Every replacement has a stable `id`, `category`, and
  `rationale` — the VS Code "Explain" view shows exactly which rule fired.
- **LLMLingua-2** ([Microsoft research](https://github.com/microsoft/LLMLingua))
  is preferred for reasoning- and creative-style prompts. If the package or the
  `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` model is
  unavailable, the engine falls back to SNS and surfaces a structured warning.
- **Auto strategy** uses a heuristic JSON model bundled in the package to
  classify prompts into `code | reasoning | qa | creative`, then picks SNS or
  LLMLingua-2. You can train a real scikit-learn classifier with
  `python -m tokensqueeze.classifier train data.jsonl` and it is picked up
  automatically.

---

## CLI

```bash
squeeze --help

# from stdin
echo "Could you please write tests that check if a list is sorted?" | squeeze

# inline
squeeze --strategy sns "Write a function that returns the sum of an array"

# JSON output (consumed by the VS Code extension)
squeeze --json --strategy sns "Please write a Python function that reverses a string"

# show which rules fired
squeeze --explain "Please write a function that returns the result as JSON"
```

Token counts use `tiktoken` (cl100k_base) when installed; otherwise a
regex word/punct counter calibrated to track BPE on prose.

---

## HTTP API / server

```bash
# local server
uvicorn server.main:app --host 127.0.0.1 --port 8765

# or via Docker
docker build -t tokensqueeze:0.1.0 -f server/Dockerfile .
docker run --rm -p 8765:8765 tokensqueeze:0.1.0
```

| Method | Path        | Description                                        |
| ------ | ----------- | -------------------------------------------------- |
| GET    | `/health`   | Liveness probe                                     |
| POST   | `/compress` | `{prompt, strategy?, encoding?, explain?}` → JSON  |
| GET    | `/stats`    | Cumulative tokens saved this session               |

---

## VS Code extension

`vscode-extension/` is a TypeScript extension. It calls
`python -m tokensqueeze.cli --json` so your Python install stays local.

- **TokenSqueeze: Compress Selection** — `Ctrl+Shift+S` / `Cmd+Shift+S`
- **TokenSqueeze: Explain Compression (Side-by-Side)** — `Ctrl+Shift+Alt+S`
- Status bar shows live approximate token count for the current selection.
- Side-by-side webview shows original / compressed / per-rule trace.

```bash
cd vscode-extension && npm install && npm run compile
# Press F5 in VS Code with the folder open to launch the Extension Host.
```

> **Not yet on the VS Code Marketplace** — that listing is forthcoming.
> Use the build instructions above to load the extension locally.

---

## Browser extension (Manifest V3)

`browser-extension/` is a static MV3 extension. Load it via
`chrome://extensions` → Developer Mode → Load unpacked, then start the local
server. The content script injects a **⚡ Squeeze** button on:

- chat.openai.com / chatgpt.com
- claude.ai
- perplexity.ai
- gemini.google.com

The popup lets you change the server endpoint and strategy. Default:
`http://127.0.0.1:8765/compress`.

> **Not yet on the Chrome Web Store or Firefox AMO** — those listings are
> forthcoming. Load unpacked for now.

---

## OpenClaw plugin

`openclaw-plugin/preprocessor.sh` is a shell script compatible with any
harness that respects `$OPENCLAW_PREPROCESSOR`.

```bash
export OPENCLAW_PREPROCESSOR="$(pwd)/openclaw-plugin/preprocessor.sh"
# or, with squeeze on PATH:
export OPENCLAW_PREPROCESSOR="squeeze --strategy auto --quiet"
```

See [`openclaw-plugin/README.md`](openclaw-plugin/README.md) for env-var
config options and a sample `tokensqueeze.toml`.

---

## Comparison vs. Caveman and manual editing

| Approach | Compression method | Prompt-type awareness | Explainable | Offline | When to use |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TokenSqueeze SNS** | Regex rewrites (symbolic shorthand) | ✅ routes per type | ✅ per-rule trace | ✅ zero deps | Code, QA, structured prompts |
| **TokenSqueeze + LLMLingua-2** | SNS + semantic pruning | ✅ | Partial (token scores) | ✅ local model | Reasoning, creative writing |
| **Caveman** | Rule-based keyword removal | ❌ | ❌ | ✅ | Simple stripping |
| **Manual edit** | Human judgment | ✅ | ✅ | ✅ | One-offs you really care about |
| **Gisting** (roadmap) | Fine-tuned virtual tokens | Depends on training | ❌ | Depends | Repeated system-prompt patterns |

**Example — single canonical prompt (measured with tiktoken cl100k_base):**

| Tool | Output | Tokens | Reduction |
| :--- | :--- | :--- | :--- |
| Original | *Write a Python function that checks if a number is prime* | 12 | — |
| TokenSqueeze SNS | `isPrime(n)` | 4 | −66.7% |

> These numbers are real but represent a best-case idiom match. Savings
> on free-form or longer prompts will vary. Run the validation harness on
> your own corpus before making cost projections.

---

## Validation

```bash
# JSONL of {"prompt": "..."} rows
python -m validate.fidelity --input prompts.jsonl --strategy auto

# OpenAI HumanEval sample (needs `pip install datasets`)
python -m validate.fidelity --humaneval --strategy sns --limit 50 --report-json humaneval.json
```

Fidelity is cosine similarity when `sentence-transformers` is installed,
otherwise `difflib.SequenceMatcher.ratio()`. An LLM-judge hook is available
via `TOKENSQUEEZE_LLM_JUDGE=1` (opt-in, requires an API key).

---

## Development

```bash
make install-all      # editable install with all optional extras
make test             # pytest (43 tests)
make server           # uvicorn on 127.0.0.1:8765
make sample-validate  # quick fidelity check on 3 bundled prompts
make vscode-build     # compile the VS Code extension (needs Node.js)
```

---

## Roadmap

| Milestone | Target | Description |
| :--- | :--- | :--- |
| **v0.1** | ✅ current | Core SNS engine · CLI · FastAPI server · VS Code + browser extension source · OpenClaw preprocessor · fidelity harness |
| **v0.2** | Near-term | VS Code Marketplace listing · Chrome/Firefox store submissions · token counter widget improvements |
| **v0.3** | Experimental | LLMLingua-2 integration hardening · trained adaptive classifier + labelled dataset |
| **v0.4** | Forthcoming | Browser extension store listings · OpenClaw native integration improvements |
| **v1.0** | Long-term | Gisting module (requires fine-tuned LM) · enterprise API hardening · multilingual rule expansion |

---

## Caveats — please read

- **Numbers in this README are real but not benchmarks.** The −66.7%
  reduction on `isPrime(n)` is a best-case idiom match. SNS is most
  aggressive on short, code-style prompts. Savings on prose, reasoning
  chains, or long system prompts will be lower. Use `make sample-validate`
  or the fidelity harness on your own data.
- **SNS rewrites are deterministic but lossy.** Idiom rules collapse
  canonical templates to their tightest symbolic form. For free-form
  writing, use `--strategy llmlingua2` (or `auto`) for more conservative
  compression.
- **The "auto" classifier is a heuristic JSON model.** It is sufficient to
  route between SNS and LLMLingua-2 but is not a competitive text classifier.
  Train your own: `python -m tokensqueeze.classifier train data.jsonl`.
- **Gisting is a stub.** Real gisting (Mu et al., 2023) requires a
  fine-tuned model with vocabulary extension. The module documents the
  requirements and falls back to SNS rather than silently misrepresenting
  results.
- **VS Code and browser extensions are not yet on their stores.**
  Build/load them locally using the instructions above.
- **There is no Rust tokenizer in v0.1.** Token counting uses `tiktoken`
  (optional) or a regex approximation. A faster tokenizer path is a
  potential future improvement.

---

## License

[MIT](LICENSE).

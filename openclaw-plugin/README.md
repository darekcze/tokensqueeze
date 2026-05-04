# TokenSqueeze ⇢ OpenClaw plugin

A drop-in shell preprocessor that compresses every prompt your harness sends
to an LLM. Harness reads stdin → runs `tokensqueeze.cli` → writes stdout.

## Install

1. Install the Python package: `pip install tokensqueeze`
2. Set the preprocessor:

```bash
export OPENCLAW_PREPROCESSOR="/path/to/tokensqueeze/openclaw-plugin/preprocessor.sh"
# or, if you have `squeeze` on PATH:
export OPENCLAW_PREPROCESSOR="squeeze --strategy auto --quiet"
```

3. Restart your harness.

## Configuration

| Env var | Default | Notes |
| --- | --- | --- |
| `TOKENSQUEEZE_STRATEGY` | `auto` | One of `auto`, `sns`, `llmlingua2`, `gist`. |
| `TOKENSQUEEZE_ENCODING` | `cl100k_base` | Tokenizer for stats. |
| `TOKENSQUEEZE_PYTHON` | `python` (then `python3`) | Override interpreter. |
| `TOKENSQUEEZE_DISABLE` | unset | Set to `1` to bypass without unsetting `OPENCLAW_PREPROCESSOR`. |

## Sample config

A minimal `tokensqueeze.toml` you can keep next to your harness config:

```toml
# tokensqueeze.toml — read by your own harness if it supports config files;
# the shell preprocessor reads env vars only.
[tokensqueeze]
strategy = "auto"
encoding = "cl100k_base"
disable_for = ["explain-mode", "raw-debug"]   # optional gating hints
```

## Failure modes

- If `python` isn't on PATH, or the `tokensqueeze` package isn't importable,
  the preprocessor passes the prompt through unchanged and logs to stderr.
- If a strategy needs a missing dependency (e.g. LLMLingua-2), TokenSqueeze
  itself falls back to SNS and surfaces the warning on stderr.

## Caveats

- The preprocessor compresses *every* prompt, including in-progress completions
  if your harness streams them back through the same pipe. Most don't, but
  double-check. Set `TOKENSQUEEZE_DISABLE=1` for a quick a/b sanity run.
- SNS rules are aggressive; for free-form creative writing prefer
  `--strategy llmlingua2`.

#!/usr/bin/env bash
# TokenSqueeze preprocessor for OpenClaw / Claude Code-style harnesses.
#
# Usage (in your shell rc / OpenClaw config):
#   export OPENCLAW_PREPROCESSOR="/path/to/openclaw-plugin/preprocessor.sh"
#
# Reads a prompt from stdin, runs the TokenSqueeze CLI, and writes the
# compressed prompt to stdout. Stderr is preserved for the harness to log.
#
# Configuration via env vars:
#   TOKENSQUEEZE_STRATEGY   default: auto
#   TOKENSQUEEZE_ENCODING   default: cl100k_base
#   TOKENSQUEEZE_PYTHON     default: python (or python3 if python missing)
#   TOKENSQUEEZE_DISABLE=1  to bypass and pass prompt through unchanged

set -eu

if [[ "${TOKENSQUEEZE_DISABLE:-0}" == "1" ]]; then
    cat
    exit 0
fi

STRATEGY="${TOKENSQUEEZE_STRATEGY:-auto}"
ENCODING="${TOKENSQUEEZE_ENCODING:-cl100k_base}"

if [[ -n "${TOKENSQUEEZE_PYTHON:-}" ]]; then
    PY="$TOKENSQUEEZE_PYTHON"
elif command -v python >/dev/null 2>&1; then
    PY="python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "[tokensqueeze] python not found; passing through" >&2
    cat
    exit 0
fi

# If the package isn't importable, pass through rather than break the user's flow.
if ! "$PY" -c "import tokensqueeze" >/dev/null 2>&1; then
    echo "[tokensqueeze] package not importable; passing through" >&2
    cat
    exit 0
fi

"$PY" -m tokensqueeze.cli --strategy "$STRATEGY" --encoding "$ENCODING" --quiet

#!/usr/bin/env bash
set -euo pipefail

if ! command -v node >/dev/null 2>&1; then
  echo "Error: node is required but not installed." >&2
  exit 1
fi

if ! command -v vsce >/dev/null 2>&1; then
  echo "vsce not found, installing globally..."
  npm install -g @vscode/vsce
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
mkdir -p "$DIST"

cd "$ROOT/vscode-extension"
npm ci
vsce package --out "$DIST/tokensqueeze.vsix"

echo "$DIST/tokensqueeze.vsix"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/browser-extension"
DIST="$ROOT/dist"
STAGE="/tmp/tokensqueeze-chrome"
ZIP="/tmp/tokensqueeze-browser.zip"

mkdir -p "$DIST"
rm -rf "$STAGE" "$ZIP"
mkdir -p "$STAGE"

cp "$SRC/manifest.json" "$STAGE/"
cp -r "$SRC/src" "$STAGE/"
if [ -d "$SRC/icons" ]; then
  cp -r "$SRC/icons" "$STAGE/"
fi

(cd "$STAGE" && zip -r "$ZIP" .)

mv "$ZIP" "$DIST/tokensqueeze-browser.zip"

echo "$DIST/tokensqueeze-browser.zip"

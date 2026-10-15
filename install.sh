#!/bin/sh
# Installs system deps (uv, ffmpeg, deno, compiler); Python deps are resolved by uv on first run.
set -e
have() { command -v "$1" >/dev/null 2>&1; }

if have brew; then
  have uv     || brew install uv
  have ffmpeg || brew install ffmpeg
  have deno   || brew install deno
elif have apt-get; then
  have cc     || sudo apt-get install -y build-essential
  have ffmpeg || sudo apt-get install -y ffmpeg
  have uv     || curl -LsSf https://astral.sh/uv/install.sh | sh
  have deno   || curl -fsSL https://deno.land/install.sh | sh
else
  echo "Install uv, ffmpeg and deno manually" >&2; exit 1
fi

echo "Done. Run: uv run server.py"

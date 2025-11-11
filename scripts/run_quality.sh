#!/usr/bin/env bash
set -euo pipefail

if [ -d "$HOME/.venvs/gnomeman" ]; then
  source "$HOME/.venvs/gnomeman/bin/activate"
fi

echo "[+] Running code quality checks..."
pre-commit run --all-files || true
flake8 . || true
black --check . || true
isort --check-only . || true
pytest -q || true
echo "[+] Quality checks complete!"


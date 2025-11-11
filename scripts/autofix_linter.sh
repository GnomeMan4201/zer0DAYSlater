#!/usr/bin/env bash
set -euo pipefail
if [ -d "$HOME/.venvs/gnomeman" ]; then
  source "$HOME/.venvs/gnomeman/bin/activate"
fi

echo "[+] Removing unused imports and fixing bare excepts..."
autopep8 --in-place --aggressive --recursive .
autoflake --in-place --remove-unused-variables --remove-all-unused-imports --recursive .

echo "[+] Re-running black and isort..."
black .
isort .

echo "[+] Final flake8 check..."
flake8 .
echo "[✓] Autofix complete!"

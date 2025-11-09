#!/bin/bash
set -e
echo "[*] Setting up Session Exfil OMEGA (venv+symlinks)..."

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

chmod +x omega_implant.py omega_operator_console.py

sudo ln -sf $(realpath omega_operator_console.py) /usr/local/bin/omega-operator
sudo ln -sf $(realpath omega_implant.py) /usr/local/bin/omega-implant

echo "[✓] Install complete! Run:"
echo "   omega-operator   # operator UI"
echo "   omega-implant    # deploy implant"

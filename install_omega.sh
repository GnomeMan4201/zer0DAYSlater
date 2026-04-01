#!/usr/bin/env bash
set -e

echo "[*] Setting up zer0DAYSlater..."

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[✓] Install complete."
echo ""
echo "Configure environment before use:"
echo "   export ZDS_AUTH_TOKEN=your_token"
echo "   export ZDS_C2_WS_URL=wss://your-c2-server:8765"
echo "   export ZDS_HTTPS_ENDPOINT=https://your-c2-server/api"
echo "   export ZDS_PLUGIN_SERVER=https://your-c2-server"
echo "   export ZDS_CONTROL_DOMAIN=your.c2.domain"
echo "   export ZDS_PEERS=192.168.x.x,192.168.x.y"
echo ""
echo "Then run:"
echo "   source .venv/bin/activate"
echo "   ./omega_campaign.sh"

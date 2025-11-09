#!/bin/bash
source .venv/bin/activate
clear
echo -e "\033[92m"
echo "███████╗███████╗███████╗ █████╗ ██╗     ";
echo "██╔════╝██╔════╝██╔════╝██╔══██╗██║     ";
echo "███████╗███████╗█████╗  ███████║██║     ";
echo "╚════██║╚════██║██╔══╝  ██╔══██║██║     ";
echo "███████║███████║███████╗██║  ██║███████╗";
echo "╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝";
echo -e "\033[0m"

echo "[*] Starting Session Exfil OMEGA Campaign..."

sleep 1
echo "[*] Launching operator dashboard..."
sleep 1
omega-operator

#!/usr/bin/env python3
"""
zer0DAYSlater — LANimals Integration
Sweeps local subnet using LANimals ping_sweep and writes discovered
hosts to ZDS_PEERS in .env for use by the C2 mesh.
"""
import ipaddress
import os
import re
import socket
import subprocess
import sys
import threading
from pathlib import Path
from queue import Queue

# Add LANimals to path
LANIMALS_ROOT = Path(__file__).parent.parent / "LANimals"
sys.path.insert(0, str(LANIMALS_ROOT))
sys.path.insert(0, str(LANIMALS_ROOT / "modules"))

ACTIVE = []
THREADS = 50

def ping_host(ip):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", str(ip)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            ACTIVE.append(str(ip))
    except Exception:
        pass

def sweep(subnet):
    print(f"[*] Sweeping {subnet}...")
    net = ipaddress.ip_network(subnet, strict=False)
    q = Queue()
    for ip in net.hosts():
        q.put(ip)

    def worker():
        while not q.empty():
            ip = q.get()
            ping_host(ip)
            q.task_done()

    threads = min(THREADS, q.qsize())
    for _ in range(threads):
        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()
    q.join()
    return ACTIVE

def get_local_subnet():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        # Assume /24
        parts = local_ip.rsplit(".", 1)
        return f"{parts[0]}.0/24", local_ip
    except Exception:
        return "192.168.1.0/24", "unknown"

def update_env(peers, env_path):
    peers_str = ",".join(peers)
    if not env_path.exists():
        print(f"[!] No .env found at {env_path}")
        return
    content = env_path.read_text()
    if "ZDS_PEERS=" in content:
        content = re.sub(r"ZDS_PEERS=.*", f"ZDS_PEERS={peers_str}", content)
    else:
        content += f"\nZDS_PEERS={peers_str}\n"
    env_path.write_text(content)
    print(f"[✓] ZDS_PEERS updated: {peers_str}")

if __name__ == "__main__":
    env_path = Path(__file__).parent / ".env"
    subnet, local_ip = get_local_subnet()
    print(f"[*] Local IP: {local_ip}")
    hosts = sweep(subnet)
    # Exclude self
    peers = [h for h in hosts if h != local_ip]
    print(f"[✓] Found {len(hosts)} host(s) up, {len(peers)} peer(s) (excluding self)")
    for p in peers:
        print(f"    {p}")
    if peers:
        update_env(peers, env_path)
    else:
        print("[!] No peers found — ZDS_PEERS not updated")

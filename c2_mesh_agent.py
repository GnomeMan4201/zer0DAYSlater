import os
import socket
import threading

from config import CONFIG

PEERS = [p.strip() for p in os.environ.get("ZDS_PEERS", "").split(",") if p.strip()]
FALLBACK_PORT = int(os.environ.get("ZDS_MESH_PORT", "9009"))


def receive_from_peer():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", FALLBACK_PORT))
    s.listen(1)
    print(f"[*] Mesh relay: Listening on port {FALLBACK_PORT}...")
    while True:
        conn, addr = s.accept()
        data = conn.recv(4096).decode()
        if data:
            print(f"[RELAY FROM {addr}]: {data}")
        conn.close()


def send_to_peers(message):
    for peer in PEERS:
        try:
            with socket.create_connection((peer, FALLBACK_PORT), timeout=2) as s:
                s.sendall(message.encode())
        except Exception:
            continue


def c2_main():
    if not PEERS:
        print("[!] No peers configured — set ZDS_PEERS=ip1,ip2")
        return
    threading.Thread(target=receive_from_peer, daemon=True).start()
    while True:
        cmd = input("[cmd]> ")
        send_to_peers(cmd)


if __name__ == "__main__":
    c2_main()

import socket
import threading

PEERS = ["192.168.1.101", "192.168.1.102"]
FALLBACK_PORT = 9009


def receive_from_peer():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", FALLBACK_PORT))
    s.listen(1)
    print("[*] Mesh relay: Listening for peer messages...")
    while True:
        conn, addr = s.accept()
        data = conn.recv(4096).decode()
        if data:
            print(f"[RELAY FROM {addr}]: {data}")
            # Process/forward logic here
        conn.close()


def send_to_peers(message):
    for peer in PEERS:
        try:
            with socket.create_connection((peer, FALLBACK_PORT), timeout=2) as s:
                s.sendall(message.encode())
        except BaseException:
            continue


def c2_main():
    threading.Thread(target=receive_from_peer, daemon=True).start()
    while True:
        cmd = input("[cmd]> ")
        send_to_peers(cmd)


if __name__ == "__main__":
    c2_main()

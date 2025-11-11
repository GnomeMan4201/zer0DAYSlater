import socket

import requests


def detect_proxy_settings():
    proxies = requests.utils.get_environ_proxies("http://example.com")
    return proxies if proxies else {}


def check_tor_connection():
    try:
        s = socket.create_connection(("127.0.0.1", 9050), timeout=2)
        s.close()
        return True
    except BaseException:
        return False


def check_i2p_proxy():
    try:
        s = socket.create_connection(("127.0.0.1", 4444), timeout=2)
        s.close()
        return True
    except BaseException:
        return False


def main():
    proxies = detect_proxy_settings()
    print("[INFO] Detected proxy config:", proxies)

    if check_tor_connection():
        print("[OK] Tor proxy detected on 127.0.0.1:9050")
    if check_i2p_proxy():
        print("[OK] I2P proxy detected on 127.0.0.1:4444")


if __name__ == "__main__":
    main()

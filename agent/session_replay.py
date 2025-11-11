import base64
import json

from Crypto.Cipher import AES

LOG_PATH = "session_memory.json"
KEY_PATH = "session_key.bin"


def decrypt_entry(enc_entry, key):
    raw = base64.b64decode(enc_entry)
    nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return json.loads(cipher.decrypt_and_verify(ciphertext, tag).decode())


def replay_session():
    with open(KEY_PATH, "rb") as f:
        key = f.read()

    with open(LOG_PATH, "r") as f:
        for line in f:
            try:
                data = decrypt_entry(line.strip(), key)
                print(f"[{data['time']}] ({data['type']}) - {data['data']}")
            except Exception as e:
                print(f"[!] Failed to decrypt entry: {e}")


if __name__ == "__main__":
    replay_session()

import json
import os
import base64
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

SESSION_LOG = "session_memory.json"
KEY_PATH = "session_key.bin"

def generate_key():
    if not os.path.exists(KEY_PATH):
        key = get_random_bytes(32)
        with open(KEY_PATH, "wb") as f:
            f.write(key)
    else:
        with open(KEY_PATH, "rb") as f:
            key = f.read()
    return key

def encrypt_entry(entry, key):
    cipher = AES.new(key, AES.MODE_GCM)
    enc, tag = cipher.encrypt_and_digest(json.dumps(entry).encode())
    return base64.b64encode(cipher.nonce + tag + enc).decode()

def log_event(event_type, details):
    key = generate_key()
    entry = {
        "time": datetime.utcnow().isoformat(),
        "type": event_type,
        "data": details
    }
    enc_entry = encrypt_entry(entry, key)
    with open(SESSION_LOG, "a") as f:
        f.write(enc_entry + "\n")

if __name__ == "__main__":
    log_event("exfil", {"target": "user_profiles", "size": "28KB"})
    log_event("status", {"msg": "Exfiltration completed at 01:42 UTC."})

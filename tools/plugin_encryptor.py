
import base64
import json
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def derive_key(agent_id):
    return agent_id.encode("utf-8")[:32].ljust(32, b"0")

def encrypt_plugin(raw_code: str, agent_id: str) -> str:
    key = derive_key(agent_id)
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(raw_code.encode())

    package = {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "tag": base64.b64encode(tag).decode()
    }
    return json.dumps(package)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python plugin_encryptor.py <plugin.py> <agent_id> <output.txt>")
        exit(1)

    plugin_path, agent_id, output_path = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(plugin_path, "r") as f:
        plugin_code = f.read()

    encrypted = encrypt_plugin(plugin_code, agent_id)

    with open(output_path, "w") as out:
        out.write(encrypted)
        print(f"[+] Encrypted plugin written to {output_path}")

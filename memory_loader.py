import base64
import json

from Crypto.Cipher import AES


def derive_key(agent_id):
    return agent_id.encode("utf-8")[:32].ljust(
        32, b"0"
    )  # basic 32-byte agent-specific key


def load_encrypted_plugin(encrypted_blob, agent_id):
    try:
        blob = json.loads(encrypted_blob.decode())
        nonce = base64.b64decode(blob["nonce"])
        ciphertext = base64.b64decode(blob["ciphertext"])
        tag = base64.b64decode(blob["tag"])
        key = derive_key(agent_id)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        decrypted = cipher.decrypt_and_verify(ciphertext, tag)
        exec(decrypted, {})
    except Exception as e:
        print(f"[!] Plugin Load Failed: {e}")

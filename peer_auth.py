import base64

import nacl.utils
from nacl.encoding import Base64Encoder
from nacl.public import Box, PrivateKey, PublicKey

# Generate a new keypair per peer (persist this for real use)
PRIVATE_KEY = PrivateKey.generate()
PUBLIC_KEY = PRIVATE_KEY.public_key


def get_public_key_b64():
    return PUBLIC_KEY.encode(encoder=Base64Encoder).decode()


def encrypt_for_peer(peer_public_b64, message: str) -> str:
    peer_key = PublicKey(
        base64.b64decode(peer_public_b64), encoder=nacl.encoding.RawEncoder
    )
    box = Box(PRIVATE_KEY, peer_key)
    nonce = nacl.utils.random(Box.NONCE_SIZE)
    encrypted = box.encrypt(message.encode(), nonce)
    return base64.b64encode(encrypted).decode()


def decrypt_from_peer(peer_public_b64, encrypted_b64: str) -> str:
    peer_key = PublicKey(
        base64.b64decode(peer_public_b64), encoder=nacl.encoding.RawEncoder
    )
    box = Box(PRIVATE_KEY, peer_key)
    decrypted = box.decrypt(base64.b64decode(encrypted_b64))
    return decrypted.decode()

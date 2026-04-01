# zer0DAYSlater — Architecture Walkthrough

---

## Operator Pipeline (NL → action → execution)

The operator pipeline is the spine of the whole system. Everything else
is a gate that sits on top of it.

### Step 1 — You type a natural language command

The entry point is `llm_operator.py`. You don't type a command with flags
or syntax — you type intent in plain English:

    "exfil ssh keys and credentials after 3pm, low noise"

Before that string ever reaches the LLM, time expressions get pre-resolved
to ISO timestamps. Mistral is bad at time arithmetic, so the framework
handles it before the model sees it. Temperature is set to 0.1 for
deterministic output.

### Step 2 — Mistral parses intent into a structured action object

The LLM returns a typed dict with six fields:

    {
      "action":    "exfil",
      "targets":   ["ssh_keys", "credentials"],
      "schedule":  "2025-11-09T15:00:00+00:00",
      "priority":  "normal",
      "noise":     "silent",
      "rationale": "Operator wants credential exfil deferred to afternoon window."
    }

The rationale field is not decorative — it gets consumed downstream by
the entropy capsule to check whether the model's explanation actually
matches what it decided.

### Step 3 — The action object hits two monitoring gates before anything executes

First the entropy capsule scores the LLM output itself — how confident
was the model, did it hallucinate targets not in your command, did
coherence drop. Then the drift monitor scores the action against your
session baseline — is this within scope, or is the agent starting to
wander. Either gate can emit WARN or HALT and stop execution before it
propagates.

### Step 4 — If both gates pass, agent_core executes

`agent_core.py` takes the validated action object, selects a payload
personality via the mutator, routes through the adaptive channel manager,
and relays over the mTLS mesh to the actual target. Results come back
through the same mesh and feed fitness scores back into the mutator for
the next generation.

**Key architectural insight:** the LLM is not trusted to execute — it is
trusted only to parse. Every decision it makes gets independently scored
before anything real happens.

---

## Monitoring Layers (drift + entropy)

Two separate systems. They measure different things and fail
independently — that is intentional.

### Drift monitor — session_drift_monitor.py

Watches *what the agent decides* across the session. Builds a baseline
from your first command — scope, noise level, schedule, targets — and
scores every subsequent action against that baseline.

Six signal types:

    semantic_drift    — action type changed from what you established
    scope_creep       — new targets appeared outside original scope
    structural_decay  — action object missing fields or malformed
    noise_violation   — noise level escalated beyond what you set
    schedule_slip     — timing constraints being ignored
    parse_failure     — LLM could not produce valid structured output

Scoring is weighted, repetition-amplified, and recency-decayed. One
scope_creep is a signal. Three in a row is a pattern and the weight
compounds. Old signals decay so a clean run can recover from WARN back
toward NOMINAL.

Thresholds:

    NOMINAL → WARN → HALT   (0.0 – 1.0)

HALT is a hard stop. Execution does not continue.

### Entropy capsule — entropy_capsule.py

Watches *how confidently the model decided*, not what it decided.
Instruments the LLM output stream directly.

Five signal types:

    token_entropy         — Shannon entropy on rationale text.
                            High entropy = uncertain or rambling model.
    hallucination         — targets in output not grounded in your command.
    coherence_drift       — rationale does not explain the action taken.
    confidence_collapse   — model explanation missing or near-empty.
    instability_spike     — sudden delta between consecutive entropy scores.
                            Catches model degradation between actions.

States:

    NOMINAL → ELEVATED → CRITICAL

Can halt independently of the drift monitor.

### Why two separate systems

Drift catches *behavioral* problems — the agent doing things outside your
intent. Entropy catches *cognitive* problems — the model losing coherence
even while producing syntactically valid output.

A compromised or degraded model could pass drift checks while failing
entropy, or vice versa. You need both gates because they fail in
different directions.

The rationale field from the LLM is the bridge between them — drift
ignores it, entropy depends on it entirely.

---

## Payload Mutation + Channel Selection

Two coupled systems. The mutator decides *how* the payload behaves.
The channel manager decides *where* it travels.

### Payload mutator — payload_mutator.py

Six personalities, each with a behavioral profile:

    scout      — minimal footprint, reconnaissance bias
    ghost      — maximum stealth, slow and quiet
    leech      — persistent, low-bandwidth drain
    phantom    — evasion-first, decoy-heavy
    parasite   — embeds into existing processes
    surgeon    — precise, targeted, clean

Each personality has a fitness score that starts neutral and evolves
across the session. Five mutation ops applied per generation:

    rotate     — switch personality entirely
    morph      — mutate behavior within current personality
    fragment   — split payload into smaller chunks
    delay      — insert timing jitter
    decoy      — emit noise traffic alongside real payload

**The feedback loop is what makes it adaptive.** After each channel
attempt the result — success or detected — feeds back into the mutator.
Detection penalizes fitness. Success boosts it. The mutator tracks which
personality + op combination worked on which channel in this session and
biases toward it.

High drift + high entropy from the monitoring layer triggers forced
personality rotation regardless of fitness, because the session state is
no longer trustworthy.

### Adaptive channel manager — core/adaptive_channel_manager.py

Five transport channels:

    HTTPS      — standard, highest compatibility
    WebSocket  — persistent connection, lower overhead
    DNS        — covert, slow, high detection risk
    MQTT       — pub/sub, useful in IoT-adjacent environments
    ICMP       — deepest covert channel, most restricted

Selection is weighted by channel feedback the same way personality
fitness works. A channel that got detected gets downweighted. The manager
maintains a fallback chain so if the primary channel fails mid-session it
rolls to the next viable option without operator intervention.

`proxy_fallback_check.py` handles C2 reachability before committing to
a channel.

### How they work together

The mutator picks personality and ops. The channel manager picks
transport. Both are updated by the same feedback signal after each
execution. Over a session they co-evolve: the personality that works best
on the channel that works best gets progressively more weight until
something changes and they adapt again.

---

## mTLS Mesh + Peer Auth

The transport security layer everything else rides on.
No plaintext ever crosses it.

### Key generation

Every node generates an ephemeral NaCl keypair on startup:

    Curve25519        — key exchange
    XSalsa20/Poly1305 — authenticated encryption

Ephemeral means the keypair lives only for that session. No persistent
key material on disk that can be recovered later.

### Handshake

Before any data relay, peers go through a signed handshake. The token
is time-bounded — 30 second replay protection window. A token from 31
seconds ago is rejected even if cryptographically valid. This closes the
replay attack surface where a captured handshake gets reused to
impersonate a legitimate peer.

`peer_auth.py` handles NaCl symmetric key confirmation that both sides
derived the same shared secret from the Curve25519 exchange.

If a peer fails verification at any point it gets quarantined — not
retried, not flagged for later, quarantined immediately. That peer is
excluded from the mesh topology for the rest of the session.

### Mesh topology

Dynamic, not static. Peer list propagates across the mesh so nodes
discover each other without central coordination. Dead peers pruned every
30 seconds. Frame format is length-prefixed with 10MB max frame size —
prevents buffer overflow and memory exhaustion from oversized frames.

`mtls_mesh.py` handles the relay layer — encrypted traffic hops between
peers rather than going directly to C2, so no single node has the full
picture of what is happening.

### Why this architecture matters

Most frameworks assume trusted network. This one assumes the network is
hostile by default.

    Ephemeral keys        — key compromise after the fact recovers nothing
    Quarantine-not-retry  — compromised peer cannot keep probing
    Time-bounded tokens   — captured traffic cannot be replayed
    Mesh topology         — no single interception point sees full session

---

## Full Pipeline
```
you type intent
    → llm_operator        parses to structured action object
    → entropy_capsule     gates on model confidence + coherence
    → session_drift_monitor  gates on behavioral deviation from baseline
    → payload_mutator     selects personality + mutation ops
    → adaptive_channel_manager  selects transport channel
    → mtls_mesh           relays encrypted over verified peers
    → agent_core          executes
    → feedback returns through mesh
    → mutator + channel manager update fitness scores
    → next action
```

Every layer is independently failable, independently auditable, and
feeds the next.

---

*zer0DAYSlater // badBANANA research // GnomeMan4201*

# zer0DAYSlater — Research Notes

*badBANANA research // GnomeMan4201*

---

## Thesis

Most post-exploitation frameworks treat the operator as infallible and the
agent as deterministic. Neither assumption holds in practice.

Operators issue ambiguous commands. LLMs misparse intent. Sessions drift
from their stated objectives. Payloads get detected and the framework has
no memory of why. Peers relay data without verifying who they're talking to.

zer0DAYSlater is built around the opposite assumptions:

- The operator's intent must be parsed, not assumed
- The agent's reasoning must be monitored, not trusted
- Payload selection must be informed by what failed, not reset each session
- Peer trust must be earned cryptographically, not granted by proximity

---

## Problem 1 — The operator interface problem

Existing frameworks use fixed command syntax. The operator learns the
framework's language. This is the wrong relationship.

A natural language interface inverts it — the framework learns the
operator's language. But naive NL parsing (regex, keyword matching)
produces brittle results. The operator says "stay quiet" and the
framework has no idea what that means structurally.

**Solution implemented:** A local Mistral instance parses operator commands
into structured action objects with typed fields: action, targets, schedule,
priority, noise level, and a rationale field the model uses to explain its
interpretation. Time expressions are pre-resolved before the LLM call to
eliminate hallucination on time arithmetic. Temperature is fixed at 0.1 for
deterministic structured output.

**What this doesn't solve:** The parser still fails on highly ambiguous
commands. "Do the usual thing" produces garbage output. The framework
has no memory of what "the usual thing" means across sessions. Session
memory for operator preference learning is an open problem.

---

## Problem 2 — The reasoning degradation problem

An LLM-operated agent that cannot detect when its own reasoning is
degrading is a liability, not a capability.

Most LLM agent frameworks assume model output is either correct or
incorrect — a binary. In practice, model output degrades on a spectrum.
Rationale becomes vague. Targets drift from the operator's stated scope.
Structural fields start returning null. The model is still technically
functioning but its outputs are no longer trustworthy.

By the time a binary failure occurs, the agent may have already taken
actions inconsistent with operator intent.

**Solution implemented:** Two monitoring layers between parser and dispatcher.

The **session drift monitor** watches behavioral signals — semantic drift
from baseline action type, scope creep beyond stated targets, noise level
violations, structural decay in output fields. Scoring is weighted by signal
type, amplified by repetition, decayed by recency. WARN at 0.40, HALT at 0.70.

The **entropy capsule engine** watches confidence signals — Shannon entropy
on rationale text, hallucination detection (targets not grounded in input
command), coherence scoring between rationale and stated action, instability
spikes between adjacent capsules. These are the same signals geeknik's
Gödel's Therapy Room measures from outside the model. We measure them
from inside the agent.

**What this doesn't solve:** Both monitors use heuristic scoring. A model
that degrades slowly and consistently may never trigger a threshold spike.
Calibration of WARN/HALT thresholds for different models and operation
types is unsolved. The monitors also have no way to distinguish deliberate
operator intent changes from model drift — they rely on the operator
issuing a reset when changing objectives.

---

## Problem 3 — The payload amnesia problem

Most frameworks treat each payload attempt as independent. If DNS exfil
gets detected, the operator manually switches to HTTPS. If a persistence
mechanism gets flagged, the operator manually tries a different one.

This is manual work the framework should be doing. The agent has all the
information needed to learn what works: which channels succeed, which
personalities get detected, which mutation operators reduce noise. It just
never records or uses it.

**Solution implemented:** A fitness-scored mutation engine with six
personalities (scout / ghost / leech / phantom / parasite / surgeon),
each with domain affinities and noise constraints. Channel feedback updates
fitness scores each generation — success boosts, detection penalizes,
failure without detection decays. High drift and high entropy trigger
forced personality rotation. Action affinity filtering ensures the right
personality is selected for the current operation type.

Inspired by the chain mutation engine (`github.com/GnomeMan4201/chain`),
rebuilt as a clean typed API integrated with the operator pipeline.

**What this doesn't solve:** Fitness scores reset between sessions.
Cross-session learning — building a persistent model of what works against
a specific target environment — requires persistent storage and raises
significant operational security questions about what gets written to disk.
This is intentionally left unsolved. The tradeoff between adaptive
intelligence and operational security hygiene is a genuine open problem,
not an implementation gap.

---

## Problem 4 — The mesh trust problem

Peer-to-peer C2 meshes typically authenticate with pre-shared keys or
no authentication at all. A compromised peer can relay arbitrary data to
the rest of the mesh. A rogue node can inject commands.

**Solution implemented:** Ephemeral NaCl keypairs generated per node at
startup (Curve25519). Signed handshakes with 30-second replay protection
windows prevent token reuse. All relay traffic encrypted with
XSalsa20/Poly1305. Peers that fail verification are quarantined — not
retried, not trusted at reduced privilege. Dynamic topology with dead
peer pruning prevents stale nodes from accumulating in the mesh.

**What this doesn't solve:** Ephemeral keys mean a restarted node is
unknown to the mesh and must re-handshake with all peers. There is no
persistent identity — a node cannot prove it is the same node that
participated in a previous session. For long-running operations this is
a significant limitation. A persistent identity layer with key rotation
is an open problem.

---

## Open problems

1. **Session memory for operator preference learning** — the LLM operator
   has no memory of previous sessions. "Do the usual thing" is meaningless.

2. **Drift monitor calibration** — WARN/HALT thresholds are fixed. They
   should be model-specific and operation-type-specific.

3. **Cross-session fitness persistence** — the mutation engine's fitness
   scores reset. Persistent learning requires solving the disk-write OPSEC
   problem.

4. **Persistent mesh identity** — ephemeral keys mean nodes cannot prove
   continuity of identity across sessions.

5. **Gradual degradation detection** — both monitors use threshold-based
   scoring. A model that degrades below detection threshold consistently
   is invisible to the current implementation.

---

## Related work

- geeknik/glitch-gremlin-ai — adversarial LLM benchmarking from outside
  the model. zer0DAYSlater's entropy capsule is the agent-side mirror.
- toxy4ny/nikki-ai — offline LLM red team assistant. Shares the
  "phones home to nothing" design principle.
- Cobalt Strike, Sliver, Havoc — established C2 frameworks. None
  implement operator intent monitoring or adaptive mutation with feedback.

---

*For authorized red team operations and security research in controlled*
*environments only.*

*zer0DAYSlater // badBANANA research // GnomeMan4201*

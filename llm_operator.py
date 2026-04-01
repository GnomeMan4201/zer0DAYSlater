#!/usr/bin/env python3
"""
zer0DAYSlater — LLM Operator Interface
Replaces regex-based command parsing with a real Mistral-backed intent extractor.
Offline. No API key. No network calls. Phones home to nothing.

Parses operator natural language into structured action objects:
  {
    "action":   "exfil" | "persist" | "lateral" | "cloak" | "recon" | null,
    "targets":  ["user_profiles", "credentials", "ssh_keys", ...],
    "schedule": <unix timestamp> | null,
    "priority": "low" | "normal" | "high",
    "noise":    "silent" | "normal" | "aggressive",
    "rationale": "<model's interpretation of operator intent>"
  }
"""
from __future__ import annotations

import json
import os
import re
import datetime
from typing import Any

import ollama

# ── Configuration ─────────────────────────────────────────────────────────────

MODEL = os.environ.get("ZDS_LLM_MODEL", "mistral:latest")

SYSTEM_PROMPT = """You are the command parser for zer0DAYSlater, an operator-controlled
post-exploitation framework running in an authorized red team environment.

Your job is to parse operator intent from natural language into a structured JSON action object.

RULES:
- Respond ONLY with a valid JSON object. No explanation. No markdown. No code fences.
- If you cannot determine a field with confidence, set it to null.
- Never invent targets or actions not implied by the operator's words.
- Preserve the operator's intent precisely — do not expand or restrict scope.

OUTPUT SCHEMA:
{{
  "action":    one of ["exfil", "persist", "lateral", "cloak", "recon"] or null,
  "targets":   array of strings describing what to act on, or [],
  "schedule":  ISO 8601 datetime string for deferred execution, or null,
  "priority":  one of ["low", "normal", "high"],
  "noise":     one of ["silent", "normal", "aggressive"],
  "rationale": one sentence explaining your interpretation of operator intent
}}

TIME REFERENCE: Current UTC time is {utc_now}

EXAMPLES:

Input: "exfil user profiles and ssh keys after midnight, stay quiet"
Output: {{"action":"exfil","targets":["user_profiles","ssh_keys"],"schedule":"{midnight_iso}","priority":"normal","noise":"silent","rationale":"Operator wants credential and key exfiltration deferred to low-activity window with minimal noise."}}

Input: "persist across reboot, low noise"
Output: {{"action":"persist","targets":[],"schedule":null,"priority":"normal","noise":"silent","rationale":"Operator wants persistence mechanisms installed quietly with no specific target filter."}}

Input: "move laterally to the domain controller"
Output: {{"action":"lateral","targets":["domain_controller"],"schedule":null,"priority":"high","noise":"normal","rationale":"Operator wants lateral movement toward domain controller immediately."}}

Input: "cloak the agent process, high priority"
Output: {{"action":"cloak","targets":[],"schedule":null,"priority":"high","noise":"silent","rationale":"Operator wants process identity concealment at high priority."}}
"""


# ── Time helpers ──────────────────────────────────────────────────────────────

def _next_midnight_iso() -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = now + datetime.timedelta(days=1)
    midnight = datetime.datetime(
        tomorrow.year, tomorrow.month, tomorrow.day,
        0, 1, 0, tzinfo=datetime.timezone.utc
    )
    return midnight.isoformat()


def _resolve_time_expression(expr: str) -> str | None:
    """
    Pre-process natural language time expressions into ISO strings
    before sending to the model — reduces hallucination on time math.
    """
    expr_lower = expr.lower()
    now = datetime.datetime.now(datetime.timezone.utc)

    if "midnight" in expr_lower:
        return _next_midnight_iso()

    match = re.search(r"after\s+(\d{1,2})\s*(am|pm)", expr_lower)
    if match:
        hour = int(match.group(1))
        if match.group(2) == "pm" and hour < 12:
            hour += 12
        elif match.group(2) == "am" and hour == 12:
            hour = 0
        scheduled = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if scheduled <= now:
            scheduled += datetime.timedelta(days=1)
        return scheduled.isoformat()

    match = re.search(r"in\s+(\d+)\s*(minute|hour|min|hr)s?", expr_lower)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        delta = datetime.timedelta(
            minutes=amount if "min" in unit else 0,
            hours=amount if "hour" in unit or "hr" in unit else 0,
        )
        return (now + delta).isoformat()

    return None


# ── Core parser ───────────────────────────────────────────────────────────────

def parse_operator_command(command: str) -> dict[str, Any]:
    """
    Parse a natural language operator command using Mistral.
    Returns a structured action object.
    Falls back to null-action dict on any failure — never raises.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    pre_resolved_time = _resolve_time_expression(command)

    # Inject current time context so model doesn't hallucinate time math
    system = SYSTEM_PROMPT.format(
        utc_now=now_utc.isoformat(),
        midnight_iso=_next_midnight_iso(),
    )

    # If we pre-resolved a time expression, tell the model explicitly
    user_prompt = command
    if pre_resolved_time:
        user_prompt = (
            f"{command}\n\n"
            f"[System note: time expression resolved to {pre_resolved_time}]"
        )

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_prompt},
            ],
            options={
                "temperature": 0.1,   # low temp — we want deterministic structured output
                "top_p": 0.9,
                "num_predict": 300,
            },
        )

        raw = response["message"]["content"].strip()

        # Strip markdown fences if model adds them anyway
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        raw = raw.strip()

        parsed = json.loads(raw)

        # Validate required keys — fill missing with safe defaults
        result = {
            "action":    parsed.get("action"),
            "targets":   parsed.get("targets", []),
            "schedule":  parsed.get("schedule") or pre_resolved_time,
            "priority":  parsed.get("priority", "normal"),
            "noise":     parsed.get("noise", "normal"),
            "rationale": parsed.get("rationale", ""),
            "_raw":      raw,
            "_model":    MODEL,
            "_error":    None,
        }

        # Validate action is known
        valid_actions = {"exfil", "persist", "lateral", "cloak", "recon"}
        if result["action"] and result["action"] not in valid_actions:
            result["action"] = None
            result["_error"] = f"Unknown action: {parsed.get('action')}"

        return result

    except json.JSONDecodeError as e:
        return _null_result(command, f"JSON parse failed: {e} | raw: {raw[:200]}")
    except Exception as e:
        return _null_result(command, str(e))


def _null_result(command: str, error: str) -> dict[str, Any]:
    return {
        "action":    None,
        "targets":   [],
        "schedule":  None,
        "priority":  "normal",
        "noise":     "normal",
        "rationale": "",
        "_raw":      "",
        "_model":    MODEL,
        "_error":    error,
    }


# ── Interactive operator console ──────────────────────────────────────────────

def operator_console() -> None:
    print(f"\n[zer0DAYSlater] LLM Operator Interface — model: {MODEL}")
    print("[zer0DAYSlater] Type a command in plain English. 'quit' to exit.\n")

    while True:
        try:
            cmd = input("operator> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Session ended.")
            break

        if cmd.lower() in ("quit", "exit", "q"):
            break
        if not cmd:
            continue

        print("[*] Parsing intent...", flush=True)
        result = parse_operator_command(cmd)

        if result["_error"]:
            print(f"[!] Parse error: {result['_error']}")
        else:
            print(f"\n[+] Action:    {result['action']}")
            print(f"[+] Targets:   {result['targets']}")
            print(f"[+] Schedule:  {result['schedule']}")
            print(f"[+] Priority:  {result['priority']}")
            print(f"[+] Noise:     {result['noise']}")
            print(f"[+] Rationale: {result['rationale']}\n")


if __name__ == "__main__":
    operator_console()

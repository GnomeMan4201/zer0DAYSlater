#!/usr/bin/env python3
"""
zer0DAYSlater — Tools test suite.
Tests session_report and compare_sessions modules.
"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from entropy_capsule import EntropyCapsuleEngine
from payload_mutator import PayloadMutator, ChannelFeedback
from session_drift_monitor import SessionDriftMonitor


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_session(actions=None):
    """Build a populated drift/entropy/mutator triple from a list of action dicts."""
    drift   = SessionDriftMonitor()
    entropy = EntropyCapsuleEngine()
    mutator = PayloadMutator()
    if actions is None:
        actions = [
            {"action":"exfil",  "targets":["credentials"], "schedule":None,
             "priority":"normal","noise":"silent",
             "rationale":"Exfil credentials quietly.","_error":None,
             "_raw_cmd":"exfil credentials quietly"},
            {"action":"recon",  "targets":["domain_controller"], "schedule":None,
             "priority":"high",  "noise":"normal",
             "rationale":"Enumerate DC.","_error":None,
             "_raw_cmd":"recon domain controller"},
            {"action":"cloak",  "targets":[], "schedule":None,
             "priority":"high",  "noise":"silent",
             "rationale":"Conceal process identity.","_error":None,
             "_raw_cmd":"cloak now"},
        ]
    for ao in actions:
        drift.ingest(ao)
        entropy.ingest(ao, original_command=ao.get("_raw_cmd",""))
        mut = mutator.mutate(action_obj=ao,
                             entropy_score=entropy.current_entropy(),
                             drift_score=drift.drift_score)
        mutator.feedback(ChannelFeedback(
            payload_hash=mut.payload_hash,
            success=True, detected=False,
            channel="HTTPS", latency_ms=100.0,
        ))
    return drift, entropy, mutator


# ── SessionReport tests ───────────────────────────────────────────────────────

def test_session_report_imports():
    from tools.session_report import SessionReport
    assert SessionReport is not None


def test_session_report_build_returns_required_keys():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    for key in ("session_label","generated_at","overall_health",
                "drift","entropy","mutation","timeline"):
        assert key in r, f"Missing key: {key}"


def test_session_report_health_nominal_on_clean_session():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    assert r["overall_health"] in ("NOMINAL", "DEGRADED", "CRITICAL")


def test_session_report_drift_section():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    dr = r["drift"]
    for key in ("score","status","total_signals","signal_breakdown","session_actions"):
        assert key in dr, f"Missing drift key: {key}"
    assert dr["session_actions"] == 3


def test_session_report_entropy_section():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    er = r["entropy"]
    for key in ("score","status","total_signals","signal_breakdown","session_actions","capsule_history"):
        assert key in er
    assert er["session_actions"] == 3


def test_session_report_mutation_section():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    mr = r["mutation"]
    for key in ("fitness","generations","degraded_personalities",
                "top_personality","generation_summary"):
        assert key in mr
    assert mr["generations"] == 3
    assert mr["top_personality"] is not None


def test_session_report_timeline_length():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    assert len(r["timeline"]) == 3


def test_session_report_timeline_entry_keys():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    entry = r["timeline"][0]
    for key in ("action_idx","entropy","field","rationale","coherence"):
        assert key in entry


def test_session_report_label():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m, label="test_label").build()
    assert r["session_label"] == "test_label"


def test_session_report_save_writes_json():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    report = SessionReport(drift=d, entropy=e, mutator=m, label="save_test")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        report.save(path)
        data = json.loads(Path(path).read_text())
        assert data["session_label"] == "save_test"
        assert "drift" in data
    finally:
        Path(path).unlink(missing_ok=True)


def test_session_report_build_cached():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    report = SessionReport(drift=d, entropy=e, mutator=m)
    r1 = report.build()
    r2 = report.build()
    assert r1 is r2   # same object — cached


def test_session_report_print_summary_no_crash():
    from tools.session_report import SessionReport
    import io, contextlib
    d, e, m = _make_session()
    report = SessionReport(drift=d, entropy=e, mutator=m)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report.print_summary()
    output = buf.getvalue()
    assert "zer0DAYSlater" in output
    assert "DRIFT" in output
    assert "ENTROPY" in output
    assert "MUTATION" in output


def test_session_report_empty_session_no_crash():
    """SessionReport on a zero-action session should not raise."""
    from tools.session_report import SessionReport
    d = SessionDriftMonitor()
    e = EntropyCapsuleEngine()
    m = PayloadMutator()
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    assert r["overall_health"] in ("NOMINAL", "DEGRADED", "CRITICAL")


def test_session_report_critical_on_halted_drift():
    from tools.session_report import SessionReport
    d, e, m = _make_session()
    # Pump drift to HALT
    for _ in range(10):
        d.ingest({"action":None,"targets":["*","everything"],
                  "schedule":None,"priority":None,"noise":None,
                  "rationale":"","_error":"parse failed"})
    r = SessionReport(drift=d, entropy=e, mutator=m).build()
    assert r["overall_health"] == "CRITICAL"


# ── compare_sessions tests ────────────────────────────────────────────────────

def test_compare_sessions_imports():
    from tools.compare_sessions import compare
    assert callable(compare)


def test_compare_identical_sessions_all_zero_deltas():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m, label="base").to_dict()
    result = compare(r, r)
    assert result["drift"]["delta"] == 0.0
    assert result["entropy"]["delta"] == 0.0
    assert not result["health_changed"]
    for p, fd in result["mutation"]["fitness_deltas"].items():
        assert fd["delta"] == 0.0
    assert result["timeline"]["max_spike"] == 0.0


def test_compare_result_required_keys():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).to_dict()
    result = compare(r, r)
    for key in ("label_a","label_b","health_a","health_b",
                "health_changed","drift","entropy","mutation","timeline"):
        assert key in result


def test_compare_drift_keys():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).to_dict()
    result = compare(r, r)
    for key in ("score_a","score_b","delta","significant",
                "status_a","status_b","new_signals","resolved_signals"):
        assert key in result["drift"]


def test_compare_detects_health_change():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare
    # Session A — single clean action, NOMINAL health
    da = SessionDriftMonitor(); ea = EntropyCapsuleEngine(); ma = PayloadMutator()
    clean = {"action":"exfil","targets":["credentials"],"schedule":None,
             "priority":"normal","noise":"silent",
             "rationale":"Quiet exfil.","_error":None,"_raw_cmd":"exfil"}
    da.ingest(clean); ea.ingest(clean, original_command="exfil")
    ra = SessionReport(drift=da, entropy=ea, mutator=ma, label="clean").to_dict()
    # Session B — immediately degrade to CRITICAL
    db = SessionDriftMonitor(); eb = EntropyCapsuleEngine(); mb = PayloadMutator()
    db.ingest(clean)
    for _ in range(10):
        db.ingest({"action":None,"targets":["*"],"schedule":None,
                   "priority":None,"noise":None,"rationale":"",
                   "_error":"parse failed"})
    rb = SessionReport(drift=db, entropy=eb, mutator=mb, label="degraded").to_dict()
    assert rb["overall_health"] == "CRITICAL"
    result = compare(ra, rb)
    assert result["health_changed"]
    assert result["drift"]["delta"] > 0


def test_compare_detects_significant_drift_delta():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare
    # Session A — single clean action, low drift score
    da = SessionDriftMonitor(); ea = EntropyCapsuleEngine(); ma = PayloadMutator()
    clean = {"action":"exfil","targets":["credentials"],"schedule":None,
             "priority":"normal","noise":"silent",
             "rationale":"Quiet exfil.","_error":None,"_raw_cmd":"exfil"}
    da.ingest(clean); ea.ingest(clean, original_command="exfil")
    ra = SessionReport(drift=da, entropy=ea, mutator=ma).to_dict()
    # Session B — pump failures on fresh monitor to get high drift
    db = SessionDriftMonitor(); eb = EntropyCapsuleEngine(); mb = PayloadMutator()
    db.ingest(clean)
    for _ in range(8):
        db.ingest({"action":None,"targets":["*"],"schedule":None,
                   "priority":None,"noise":None,"rationale":"",
                   "_error":"parse failed"})
    rb = SessionReport(drift=db, entropy=eb, mutator=mb).to_dict()
    result = compare(ra, rb)
    assert result["drift"]["delta"] >= 0.10
    assert result["drift"]["significant"]


def test_compare_timeline_comparable_count():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).to_dict()
    result = compare(r, r)
    assert result["timeline"]["comparable"] == len(r["timeline"])


def test_compare_new_signals_detected():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare
    # A — clean session, no parse failures
    da, ea, ma = _make_session()
    ra = SessionReport(drift=da, entropy=ea, mutator=ma).to_dict()
    # B — introduce parse_failure signal
    db, eb, mb = _make_session()
    db.ingest({"action":None,"targets":[],"schedule":None,
               "priority":"normal","noise":"normal","rationale":"",
               "_error":"JSON parse failed"})
    rb = SessionReport(drift=db, entropy=eb, mutator=mb).to_dict()
    result = compare(ra, rb)
    # parse_failure should appear in new_signals if not in A
    sigs_a = set(ra["drift"].get("signal_breakdown") or {})
    sigs_b = set(rb["drift"].get("signal_breakdown") or {})
    expected_new = sigs_b - sigs_a
    assert set(result["drift"]["new_signals"]) == expected_new


def test_compare_print_no_crash():
    from tools.session_report import SessionReport
    from tools.compare_sessions import compare, print_comparison
    import io, contextlib
    d, e, m = _make_session()
    r = SessionReport(drift=d, entropy=e, mutator=m).to_dict()
    result = compare(r, r)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_comparison(result)
    output = buf.getvalue()
    assert "DRIFT" in output
    assert "ENTROPY" in output
    assert "MUTATION" in output
    assert "TIMELINE" in output


from pathlib import Path

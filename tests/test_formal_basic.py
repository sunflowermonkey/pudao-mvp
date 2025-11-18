# tests/test_formal_basic.py
import json
from pathlib import Path

from pudao.gate.formal_gate import check_formal_file

BASE = Path(__file__).resolve().parents[1]

def j(res):
    return json.dumps(res, ensure_ascii=False, sort_keys=True)

def show_timing(label: str, res: dict):
    tm = res.get("timings_ms", {})
    ts = res.get("timestamps", {})
    print(
        f"[{label}] "
        f"start={ts.get('start_utc')} "
        f"smt=({ts.get('smt_start_utc')}→{ts.get('smt_end_utc')}) "
        f"end={ts.get('end_utc')} | "
        f"total={tm.get('total_ms',0):.2f}ms, "
        f"parse={tm.get('parse_ms',0):.2f}ms, "
        f"smt={tm.get('smt_ms',0):.2f}ms, "
        f"report={tm.get('report_ms',0):.2f}ms"
    )

def test_vsl_strategy_happy_path():
    path = BASE / "examples" / "strategy-chengdu-ring-vsl.yaml"
    res = check_formal_file(str(path))
    show_timing("T-001 VSL happy", res)
    assert res["status"] == "sat", j(res)
    assert res["allow"] is True, j(res)
    assert res["details"]["I4_safety"] == "ok"

def test_incident_strategy_mutual_exclusion_negative():
    path = BASE / "examples" / "strategy-cd-ring-incident-rm-vms.yaml"
    res = check_formal_file(str(path))
    show_timing("T-002 incident mutual-excl NEG", res)
    assert res["status"] == "unsat", j(res)
    assert res["allow"] is False, j(res)
    assert any("mutually_exclusive_actions" in r for r in res["reasons"]), j(res)

def test_invalid_segment_id():
    path = BASE / "examples" / "strategy-chengdu-ring-vsl.yaml"
    raw = path.read_text(encoding="utf-8").replace("cd-se-104", "cd-se-999")
    tmp = BASE / "examples" / "tmp-invalid.yaml"
    tmp.write_text(raw, encoding="utf-8")
    try:
        res = check_formal_file(str(tmp))
        show_timing("T-003 invalid segment", res)
        assert res["allow"] is False
        assert "invalid_reference" in "".join(res["reasons"]), j(res)
    finally:
        tmp.unlink(missing_ok=True)

def test_spatial_smoothness_violation():
    path = BASE / "examples" / "strategy-chengdu-ring-vsl.yaml"
    raw = path.read_text(encoding="utf-8").replace("value: 70", "value: 40", 1)
    tmp = BASE / "examples" / "tmp-vsl-bad.yaml"
    tmp.write_text(raw, encoding="utf-8")
    try:
        res = check_formal_file(str(tmp))
        show_timing("T-004 spatial smoothness", res)
        assert res["allow"] is False
        assert any("spatial_smoothness_violated" in r for r in res["reasons"]), j(res)
    finally:
        tmp.unlink(missing_ok=True)

def test_closure_without_rollback():
    path = BASE / "examples" / "strategy-cd-ring-incident-rm-vms.yaml"
    raw = path.read_text(encoding="utf-8").replace("max_revert_time_s: 600", "")
    tmp = BASE / "examples" / "tmp-no-rollback.yaml"
    tmp.write_text(raw, encoding="utf-8")
    try:
        res = check_formal_file(str(tmp))
        show_timing("T-005 closure no rollback", res)
        assert res["allow"] is False
        assert any("rollback_missing_or_infinite" in r for r in res["reasons"]), j(res)
    finally:
        tmp.unlink(missing_ok=True)

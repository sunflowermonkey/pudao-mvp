import json
from pathlib import Path

from pudao.gate.formal_gate import check_formal_file


BASE = Path(__file__).resolve().parents[1]


def j(res):
    return json.dumps(res, ensure_ascii=False, sort_keys=True)


def test_vsl_strategy_happy_path():
    path = BASE / "examples" / "strategy-chengdu-ring-vsl.yaml"
    res = check_formal_file(str(path))
    assert res["status"] == "sat", j(res)
    assert res["allow"] is True, j(res)
    assert res["details"]["I4_safety"] == "ok"


def test_incident_strategy_happy_path():
    path = BASE / "examples" / "strategy-cd-ring-incident-rm-vms.yaml"
    res = check_formal_file(str(path))
    assert res["status"] == "sat", j(res)
    assert res["allow"] is True, j(res)


def test_invalid_segment_id():
    path = BASE / "examples" / "strategy-chengdu-ring-vsl.yaml"
    raw = path.read_text(encoding="utf-8").replace("cd-se-104", "cd-se-999")
    tmp = BASE / "examples" / "tmp-invalid.yaml"
    tmp.write_text(raw, encoding="utf-8")
    res = check_formal_file(str(tmp))
    assert res["allow"] is False
    assert "invalid_reference" in "".join(res["reasons"])
    tmp.unlink()


def test_spatial_smoothness_violation():
    # 修改一个值破坏 max_delta
    path = BASE / "examples" / "strategy-chengdu-ring-vsl.yaml"
    raw = path.read_text(encoding="utf-8").replace("value: 70", "value: 40", 1)
    tmp = BASE / "examples" / "tmp-vsl-bad.yaml"
    tmp.write_text(raw, encoding="utf-8")
    res = check_formal_file(str(tmp))
    assert res["allow"] is False
    assert any("spatial_smoothness_violated" in r for r in res["reasons"])
    tmp.unlink()


def test_closure_without_rollback():
    # 删除 max_revert_time_s
    path = BASE / "examples" / "strategy-cd-ring-incident-rm-vms.yaml"
    raw = path.read_text(encoding="utf-8").replace("max_revert_time_s: 600", "")
    tmp = BASE / "examples" / "tmp-no-rollback.yaml"
    tmp.write_text(raw, encoding="utf-8")
    res = check_formal_file(str(tmp))
    assert res["allow"] is False
    assert any("rollback_missing_or_infinite" in r for r in res["reasons"])
    tmp.unlink()

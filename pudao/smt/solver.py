from typing import Dict, Any, List
from pudao.dsl.models import StrategyIR
from .invariants import run_all_invariants
from .encoder import solve as smt_solve


def check_formal_with_smt(ir: StrategyIR) -> Dict[str, Any]:
    """
    返回:
    {
      "allow": bool,
      "status": "sat"|"unsat"|"unknown",
      "reasons": [..],
      "details": {"I1_structure": "...", ...}
    }
    """
    details: Dict[str, str] = {}
    reasons: List[str] = []

    # I1 结构/ID 在 parser 里已经校验，若抛异常则外层转成 unsat。
    details["I1_structure"] = "ok"

    # 运行不变式 (I2-I7)
    inv_errors = run_all_invariants(ir)
    if inv_errors:
        reasons.extend(inv_errors)

    # SMT 解
    smt_status = smt_solve(ir)
    if smt_status == "unsat" and not reasons:
        reasons.append("smt_unsat_without_local_reason")

    if reasons:
        status = "unsat"
        allow = False
    else:
        status = "sat" if smt_status == "sat" else "unknown"
        allow = smt_status == "sat"

    # 填 details（简单版，可按需要细化映射）
    details["I2_spatial"] = "ok" if not any("spatial_smoothness" in r for r in reasons) else "fail"
    details["I3_temporal"] = "ok" if not any("temporal_stability" in r for r in reasons) else "fail"
    details["I4_safety"] = "ok" if not any("safety_bounds" in r for r in reasons) else "fail"
    details["I5_rollback"] = "ok" if not any("rollback" in r for r in reasons) else "fail"
    details["I6_conflict"] = "ok" if not any("mutually_exclusive" in r for r in reasons) else "fail"
    details["I7_flow"] = "ok" if not any("flow_invariants" in r for r in reasons) else "fail"

    return {
        "allow": allow,
        "status": status,
        "reasons": reasons,
        "details": details,
    }

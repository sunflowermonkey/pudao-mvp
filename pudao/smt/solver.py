# pudao/smt/solver.py
from typing import Dict, Any, List
from time import perf_counter
from datetime import datetime, timezone

from pudao.dsl.models import StrategyIR
from pudao.smt.invariants import run_all_invariants
from pudao.smt.encoder import solve as smt_solve


def _iso_utc() -> str:
    # 例如 2025-11-17T15:32:10.123Z
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def check_formal_with_smt(ir: StrategyIR) -> Dict[str, Any]:
    """
    返回:
    {
      allow: bool,
      status: "sat"|"unsat"|"unknown",
      reasons: [..],
      details: {...},
      timestamps: {
        solver_start_utc, smt_start_utc, smt_end_utc, solver_end_utc
      },
      timings_ms: {
        invariants_ms, smt_ms, solver_ms
      }
    }
    """
    # ---- 计时起点（仅 solver 内部）----
    t_solver0 = perf_counter()
    ts_solver0 = _iso_utc()

    details: Dict[str, str] = {}
    reasons: List[str] = []

    # I1 在 parser 里做过了，这里视为 ok（出错会在上层被捕获）
    details["I1_structure"] = "ok"

    # ---- 不变式检查（Python）----
    t_inv0 = perf_counter()
    inv_errors = run_all_invariants(ir)
    t_inv1 = perf_counter()
    if inv_errors:
        reasons.extend(inv_errors)

    # ---- SMT（Z3）求解 ----
    ts_smt0 = _iso_utc()
    t_smt0 = perf_counter()
    smt_status = smt_solve(ir)
    t_smt1 = perf_counter()
    ts_smt1 = _iso_utc()

    # 若 Z3 给出 unsat 且本地没有具体原因，补一条兜底
    if smt_status == "unsat" and not reasons:
        reasons.append("smt_unsat_without_local_reason")

    # 合成总体 verdict
    if reasons:
        status = "unsat"
        allow = False
    else:
        status = "sat" if smt_status == "sat" else "unknown"
        allow = (status == "sat")

    # ---- 计时终点（仅 solver 内部）----
    t_solver1 = perf_counter()
    ts_solver1 = _iso_utc()

    # 标准化 details（与现有实现保持一致）
    details["I2_spatial"] = "ok" if not any("spatial_smoothness" in r for r in reasons) else "fail"
    details["I3_temporal"] = "ok" if not any("temporal_stability" in r for r in reasons) else "fail"
    details["I4_safety"]  = "ok" if not any("safety_bounds" in r  for r in reasons) else "fail"
    details["I5_rollback"]= "ok" if not any("rollback" in r       for r in reasons) else "fail"
    details["I6_conflict"]= "ok" if not any("mutually_exclusive" in r for r in reasons) else "fail"
    details["I7_flow"]    = "ok" if not any("flow_invariants" in r for r in reasons) else "fail"

    return {
        "allow": allow,
        "status": status,
        "reasons": reasons,
        "details": details,
        "timestamps": {
            "solver_start_utc": ts_solver0,
            "smt_start_utc": ts_smt0,
            "smt_end_utc": ts_smt1,
            "solver_end_utc": ts_solver1,
        },
        "timings_ms": {
            "invariants_ms": (t_inv1 - t_inv0) * 1000.0,
            "smt_ms": (t_smt1 - t_smt0) * 1000.0,
            "solver_ms": (t_solver1 - t_solver0) * 1000.0,  # (不变式 + SMT + 轻量封装)
        },
    }

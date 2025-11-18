# pudao/gate/formal_gate.py
import json
from time import perf_counter
from datetime import datetime, timezone
from typing import Dict, Any

from pudao.dsl.parser import load_strategy_ir
from pudao.smt.solver import check_formal_with_smt
from pudao.evidence.evidence import append_formal_timing


def _iso_utc() -> str:
    """返回形如 2025-11-17T15:32:10.123Z 的 UTC 时间戳（毫秒精度）。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def check_formal_file(path: str) -> Dict[str, Any]:
    """
    对给定策略文件执行 Formal 校验（解析 -> 不变式 -> SMT），
    返回结构化结论，并将证据落盘（NDJSON）。
    """
    # ---- 用例起点（含解析阶段）----
    t0 = perf_counter()
    ts0 = _iso_utc()

    try:
        ir = load_strategy_ir(path)
        t_parse_end = perf_counter()
        ts_parse_end = _iso_utc()
    except Exception as e:
        # 解析/Schema/ID 失败：仍返回时间戳与耗时，并写 evidence
        t_end = perf_counter()
        ts_end = _iso_utc()
        total_ms = (t_end - t0) * 1000.0

        failure_payload: Dict[str, Any] = {
            "allow": False,
            "status": "unsat",
            "reasons": [str(e)],
            "details": {"I1_structure": "fail"},
            "timestamps": {
                "start_utc": ts0,
                "parse_end_utc": ts_end,  # 解析阶段即失败结束
                "end_utc": ts_end
            },
            "timings_ms": {
                "total_ms": total_ms,
                "parse_ms": total_ms,
                "smt_ms": 0.0,
                "report_ms": 0.0
            },
        }

        # 写入 evidence
        append_formal_timing(path, failure_payload)
        return failure_payload

    # ---- 进入 Formal（含不变式 + SMT）----
    solver_res = check_formal_with_smt(ir)

    # ---- 用例终点（报告封装时间）----
    t_end = perf_counter()
    ts_end = _iso_utc()

    # 组合耗时
    parse_ms = (t_parse_end - t0) * 1000.0
    solver_ms = float(solver_res.get("timings_ms", {}).get("solver_ms", 0.0))
    total_ms = (t_end - t0) * 1000.0
    report_ms = max(0.0, total_ms - parse_ms - solver_ms)

    # 组合时间戳（兼容 solver_res 中的字段）
    ts_solver = solver_res.get("timestamps", {}) or {}
    timestamps = {
        "start_utc": ts0,
        "parse_end_utc": ts_parse_end,
        "smt_start_utc": ts_solver.get("smt_start_utc"),
        "smt_end_utc": ts_solver.get("smt_end_utc"),
        "end_utc": ts_end,
    }

    # 合并结果（在 solver_res 基础上补齐/覆盖 timing 与 timestamps）
    merged: Dict[str, Any] = dict(solver_res)
    merged["timestamps"] = timestamps
    merged["timings_ms"] = {
        **(solver_res.get("timings_ms", {}) or {}),
        "parse_ms": parse_ms,
        "report_ms": report_ms,
        "total_ms": total_ms,
    }

    # 写入 evidence
    append_formal_timing(path, merged)
    return merged


def check_formal_file_json(path: str) -> str:
    """同上，但以 JSON 字符串形式返回，方便 CLI 直接打印。"""
    res = check_formal_file(path)
    return json.dumps(res, ensure_ascii=False, indent=2)

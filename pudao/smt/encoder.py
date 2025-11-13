from typing import Dict
from z3 import Solver, Int, And, Abs, sat
from pudao.dsl.models import StrategyIR


def build_solver(ir: StrategyIR) -> Solver:
    s = Solver()
    g = ir.guardrails

    # 为 scope 内所有 segments 设置 vsl 变量（如果有 vsl 动作则约束等于该值）
    vsl_vars: Dict[str, Int] = {}

    for seg in ir.scope.segments:
        v = Int(f"vsl_{seg}")
        s.add(v >= int(g.min_vsl), v <= int(g.max_vsl))
        vsl_vars[seg] = v

    for act in ir.actions:
        if act.type == "vsl" and act.segment_id and act.value is not None:
            seg = act.segment_id
            if seg not in vsl_vars:
                vsl_vars[seg] = Int(f"vsl_{seg}")
                s.add(vsl_vars[seg] >= int(g.min_vsl), vsl_vars[seg] <= int(g.max_vsl))
            s.add(vsl_vars[seg] == int(act.value))

    # 示例：添加空间平滑约束（与 invariants 一致）
    neighbors = {
        "cd-se-101": ["cd-se-102"],
        "cd-se-102": ["cd-se-101", "cd-se-103"],
        "cd-se-103": ["cd-se-102", "cd-se-104"],
        "cd-se-104": ["cd-se-103"],
    }
    for seg, v in vsl_vars.items():
        if seg in neighbors:
            for nb in neighbors[seg]:
                if nb in vsl_vars:
                    s.add(Abs(v - vsl_vars[nb]) <= int(g.max_delta))

    return s


def solve(ir: StrategyIR) -> str:
    s = build_solver(ir)
    res = s.check()
    if res == sat:
        return "sat"
    return "unsat"

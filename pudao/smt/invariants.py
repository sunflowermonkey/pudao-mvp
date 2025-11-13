from typing import List, Tuple, Dict, Set
from pudao.dsl.models import StrategyIR, Action


def check_spatial_smoothness(ir: StrategyIR) -> List[str]:
    # I2: 相邻限速差 — MVP: 只对示例手动定义邻接
    neighbors = {
        "cd-se-101": ["cd-se-102"],
        "cd-se-102": ["cd-se-101", "cd-se-103"],
        "cd-se-103": ["cd-se-102", "cd-se-104"],
        "cd-se-104": ["cd-se-103"],
    }
    vsl_map: Dict[str, float] = {}
    for act in ir.actions:
        if act.type == "vsl" and act.segment_id and act.value is not None:
            vsl_map[act.segment_id] = act.value

    errs: List[str] = []
    max_delta = ir.guardrails.max_delta
    for seg, v in vsl_map.items():
        if seg not in neighbors:
            continue
        for nb in neighbors[seg]:
            if nb in vsl_map:
                dv = abs(vsl_map[seg] - vsl_map[nb])
                if dv > max_delta:
                    errs.append(
                        f"spatial_smoothness_violated: |vsl({seg})-vsl({nb})|={dv} > {max_delta}"
                    )
    return errs


def check_safety_bounds(ir: StrategyIR) -> List[str]:
    # I4: min/max, no zero-speed hack
    errs: List[str] = []
    g = ir.guardrails
    for act in ir.actions:
        if act.type == "vsl" and act.value is not None:
            if act.value < g.min_vsl or act.value > g.max_vsl:
                errs.append(
                    f"safety_bounds_violated: vsl({act.segment_id})={act.value} not in [{g.min_vsl},{g.max_vsl}]"
                )
            if act.value == 0:
                errs.append(
                    f"safety_bounds_violated: vsl({act.segment_id})=0 not allowed (use ramp_closure)"
                )
    return errs


def check_temporal_stability(ir: StrategyIR) -> List[str]:
    # I3 (MVP): 同一 segment 多个 VSL 冲突视为不稳定
    errs: List[str] = []
    seen: Dict[str, float] = {}
    for act in ir.actions:
        if act.type == "vsl" and act.segment_id and act.value is not None:
            if act.segment_id in seen and seen[act.segment_id] != act.value:
                errs.append(
                    f"temporal_stability_violated: multiple vsl values for {act.segment_id}"
                )
            else:
                seen[act.segment_id] = act.value
    return errs


def check_mutual_exclusion(ir: StrategyIR) -> List[str]:
    # I6: ramp_closure vs ramp_metering; multiple vms_message for same vms
    errs: List[str] = []
    ramp_modes: Dict[str, Set[str]] = {}
    vms_msgs: Dict[str, int] = {}

    for act in ir.actions:
        if act.type in ("ramp_metering", "ramp_closure") and act.ramp_id:
            ramp_modes.setdefault(act.ramp_id, set()).add(act.type)
        if act.type == "vms_message" and act.vms_id:
            vms_msgs[act.vms_id] = vms_msgs.get(act.vms_id, 0) + 1

    for ramp_id, modes in ramp_modes.items():
        if "ramp_metering" in modes and "ramp_closure" in modes:
            errs.append(
                f"mutually_exclusive_actions: ramp {ramp_id} metering+closure"
            )

    for vms_id, count in vms_msgs.items():
        if count > 1:
            errs.append(
                f"mutually_exclusive_actions: vms {vms_id} has {count} messages"
            )
    return errs


def check_rollback(ir: StrategyIR) -> List[str]:
    # I5 + I7（部分）：高风险动作必须可回滚 / 有时间上限
    errs: List[str] = []
    has_closure = any(a.type == "ramp_closure" for a in ir.actions)
    g = ir.guardrails
    ro = ir.rollout

    if has_closure:
        if ro.max_revert_time_s is None:
            errs.append("rollback_missing_or_infinite: max_revert_time_s is required")
        else:
            if g.max_closure_s is not None and ro.max_revert_time_s > g.max_closure_s:
                errs.append(
                    f"rollback_missing_or_infinite: max_revert_time_s={ro.max_revert_time_s} > max_closure_s={g.max_closure_s}"
                )

        # 如果有 closure 动作但没有 max_duration_s，也提示
        for a in ir.actions:
            if a.type == "ramp_closure" and (a.max_duration_s is None):
                errs.append(
                    "flow_invariants_violated: ramp_closure missing max_duration_s"
                )

    return errs


def run_all_invariants(ir: StrategyIR) -> List[str]:
    errs: List[str] = []
    errs.extend(check_spatial_smoothness(ir))
    errs.extend(check_temporal_stability(ir))
    errs.extend(check_safety_bounds(ir))
    errs.extend(check_mutual_exclusion(ir))
    errs.extend(check_rollback(ir))
    return errs

from typing import List, Tuple, Dict, Set
from ..dsl.models import StrategyIR, Action


def check_spatial_smoothness(ir: StrategyIR) -> List[str]:
    # I2: 相邻限速差 — MVP: 只对示例手动定义邻接
    neighbors = {
        "cd-se-101": ["cd-se-102"],
        "cd-se-102": ["cd-se-101", "cd-se-103"],
        "cd-se-103": ["cd-se-102", "cd-se-104"],
        "cd-se-104": ["cd-se-103"],
    }
    vsl_map: Dict[str, float] = {}
    for act in ir.actions:
        if act.type == "vsl" and act.segment_id and act.value is not None:
            vsl_map[act.segment_id] = act.value

    errs: List[str] = []
    max_delta = ir.guardrails.max_delta
    for seg, v in vsl_map.items():
        if seg not in neighbors:
            continue
        for nb in neighbors[seg]:
            if nb in vsl_map:
                dv = abs(vsl_map[seg] - vsl_map[nb])
                if dv > max_delta:
                    errs.append(
                        f"spatial_smoothness_violated: |vsl({seg})-vsl({nb})|={dv} > {max_delta}"
                    )
    return errs


def check_safety_bounds(ir: StrategyIR) -> List[str]:
    # I4: min/max, no zero-speed hack
    errs: List[str] = []
    g = ir.guardrails
    for act in ir.actions:
        if act.type == "vsl" and act.value is not None:
            if act.value < g.min_vsl or act.value > g.max_vsl:
                errs.append(
                    f"safety_bounds_violated: vsl({act.segment_id})={act.value} not in [{g.min_vsl},{g.max_vsl}]"
                )
            if act.value == 0:
                errs.append(
                    f"safety_bounds_violated: vsl({act.segment_id})=0 not allowed (use ramp_closure)"
                )
    return errs


def check_temporal_stability(ir: StrategyIR) -> List[str]:
    # I3 (MVP): 同一 segment 多个 VSL 冲突视为不稳定
    errs: List[str] = []
    seen: Dict[str, float] = {}
    for act in ir.actions:
        if act.type == "vsl" and act.segment_id and act.value is not None:
            if act.segment_id in seen and seen[act.segment_id] != act.value:
                errs.append(
                    f"temporal_stability_violated: multiple vsl values for {act.segment_id}"
                )
            else:
                seen[act.segment_id] = act.value
    return errs


def check_mutual_exclusion(ir: StrategyIR) -> List[str]:
    # I6: ramp_closure vs ramp_metering; multiple vms_message for same vms
    errs: List[str] = []
    ramp_modes: Dict[str, Set[str]] = {}
    vms_msgs: Dict[str, int] = {}

    for act in ir.actions:
        if act.type in ("ramp_metering", "ramp_closure") and act.ramp_id:
            ramp_modes.setdefault(act.ramp_id, set()).add(act.type)
        if act.type == "vms_message" and act.vms_id:
            vms_msgs[act.vms_id] = vms_msgs.get(act.vms_id, 0) + 1

    for ramp_id, modes in ramp_modes.items():
        if "ramp_metering" in modes and "ramp_closure" in modes:
            errs.append(
                f"mutually_exclusive_actions: ramp {ramp_id} metering+closure"
            )

    for vms_id, count in vms_msgs.items():
        if count > 1:
            errs.append(
                f"mutually_exclusive_actions: vms {vms_id} has {count} messages"
            )
    return errs


def check_rollback(ir: StrategyIR) -> List[str]:
    # I5 + I7（部分）：高风险动作必须可回滚 / 有时间上限
    errs: List[str] = []
    has_closure = any(a.type == "ramp_closure" for a in ir.actions)
    g = ir.guardrails
    ro = ir.rollout

    if has_closure:
        if ro.max_revert_time_s is None:
            errs.append("rollback_missing_or_infinite: max_revert_time_s is required")
        else:
            if g.max_closure_s is not None and ro.max_revert_time_s > g.max_closure_s:
                errs.append(
                    f"rollback_missing_or_infinite: max_revert_time_s={ro.max_revert_time_s} > max_closure_s={g.max_closure_s}"
                )

        # 如果有 closure 动作但没有 max_duration_s，也提示
        for a in ir.actions:
            if a.type == "ramp_closure" and (a.max_duration_s is None):
                errs.append(
                    "flow_invariants_violated: ramp_closure missing max_duration_s"
                )

    return errs


def run_all_invariants(ir: StrategyIR) -> List[str]:
    errs: List[str] = []
    errs.extend(check_spatial_smoothness(ir))
    errs.extend(check_temporal_stability(ir))
    errs.extend(check_safety_bounds(ir))
    errs.extend(check_mutual_exclusion(ir))
    errs.extend(check_rollback(ir))
    return errs

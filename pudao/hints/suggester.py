# pudao/hints/suggester.py
from __future__ import annotations
import os, re, json, hashlib
from typing import Any, Dict, List, Optional

# 环境开关
HINTS_ENABLE      = os.getenv("PFSB_HINTS_ENABLE", "1") == "1"          # 总开关
HINTS_USE_LLM     = os.getenv("PFSB_HINTS_USE_LLM", "0") == "1"         # 是否调用LLM润色
HINTS_MAX_BULLETS = int(os.getenv("PFSB_HINTS_MAX_BULLETS", "5"))

def _extract(obj: Dict[str, Any], key: str, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else default

def _topology_hint(ir) -> str:
    try:
        segs = _extract(ir.scope.dict(), "segments", []) if hasattr(ir, "scope") else []
        return f"当前策略涉及路段数：{len(segs)}。"
    except Exception:
        return ""

def _dedup_keep_order(items: List[str]) -> List[str]:
    seen = set(); out = []
    for x in items:
        if not x: continue
        if x in seen: continue
        seen.add(x); out.append(x)
    return out[:HINTS_MAX_BULLETS]

def suggest_deterministic(result: Dict[str, Any],
                          ir: Optional[Any] = None) -> List[str]:
    """
    基于 reasons/details 生成确定性、可复现的修复建议（不依赖LLM）。
    """
    reasons = [str(r) for r in (result.get("reasons") or [])]
    details = result.get("details") or {}

    tips: List[str] = []

    # I1 结构/引用
    if details.get("I1_structure") == "fail" or any("invalid_reference" in r or "schema_violation" in r for r in reasons):
        tips.append("检查ID/字段：确保 segment_id/ramp_id/vms_id 存在且拼写正确，必填字段齐全。")
        tips.append("如由UI模板生成，请确认未删除必填字段（如 rollout.max_revert_time_s）。")

    # I2 空间平滑
    if details.get("I2_spatial") == "fail" or any("spatial_smoothness_violated" in r for r in reasons):
        tips.append("相邻路段限速差超阈值：把相邻段的限速差收敛到 guardrails.max_delta 以内。")
        tips.append("优先调整变化更剧烈的路段，使 VSL 梯度更平滑。")

    # I3 时间稳定
    if details.get("I3_temporal") == "fail" or any("temporal_stability_violated" in r for r in reasons):
        tips.append("同一路段存在多次/冲突限速：合并为单一目标值，或放宽 max_changes_per_5min。")

    # I4 安全边界
    if details.get("I4_safety") == "fail" or any("safety_bounds_violated" in r for r in reasons):
        tips.append("限速越界：将 value 限制在 guardrails.min_vsl ~ guardrails.max_vsl 之间，禁止以 vsl=0 伪装封闭。")

    # I5 回滚可行性
    if details.get("I5_rollback") == "fail" or any("rollback_missing_or_infinite" in r for r in reasons):
        tips.append("强干预缺少回滚：补充 rollout.max_revert_time_s，且不超过 guardrails.max_closure_s。")

    # I6 互斥动作
    if details.get("I6_conflict") == "fail" or any("mutually_exclusive_actions" in r for r in reasons):
        # 尝试提取冲突对象ID
        conflict_objs = []
        for r in reasons:
            m = re.search(r"(segment|ramp|vms)\s+([A-Za-z0-9\-\_]+)", r)
            if m: conflict_objs.append(f"{m.group(1)}={m.group(2)}")
        obj_txt = f"（{', '.join(conflict_objs)}）" if conflict_objs else ""
        tips.append(f"互斥动作冲突{obj_txt}：同一对象请仅保留一种动作（例如 ramp 只能二选一：metering 或 closure）。")

    # I7 控制流/时序
    if details.get("I7_flow") == "fail" or any("flow_invariants_violated" in r for r in reasons):
        tips.append("流程约束不满足：封闭/强干预必须设置有限时长，并与回滚时间一致或更短。")

    # 兜底
    if not tips:
        if any("smt_unsat_without_local_reason" in r for r in reasons):
            tips.append("Z3 不可满足但未定位具体原因：建议逐步精简动作，只保留最小子集定位冲突。")
        else:
            tips.append("未命中标准错误模板：请检查 guardrails 与 actions 的组合是否存在隐式矛盾。")

    # 可选：补充上下文
    topo = _topology_hint(ir)
    if topo:
        tips.append(topo)

    return _dedup_keep_order(tips)

# —— 可选：LLM 润色（不影响判定，仅改善可读性） ——

def _hash_inputs(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
    return h.hexdigest()[:16]

def _compose_llm_prompt(deterministic_tips: List[str],
                        result: Dict[str, Any]) -> str:
    payload = {
        "status": result.get("status"),
        "reasons": result.get("reasons"),
        "details": result.get("details"),
        "tips": deterministic_tips[:HINTS_MAX_BULLETS],
    }
    # 中文指令，约束输出结构
    return (
        "你是交通策略校验助手。请将下面的‘机器可读修复建议’转写为面向运营同学的中文提示，要求："
        "1) 保持事实准确，不改变任何技术结论；2) 列成不超过5条的要点；3) 每条不超过40字；"
        "4) 不要输出具体执行指令；5) 只输出纯文本要点列表。\n"
        f"输入JSON：{json.dumps(payload, ensure_ascii=False)}"
    )

def generate_llm_hint(deterministic_tips: List[str],
                      result: Dict[str, Any]) -> Optional[str]:
    """
    这里仅示意：保留接口，让你接到任意大模型SDK（OpenAI/Azure/DeepSeek等）。
    默认返回 None；启用时请在外层注入实际客户端。
    """
    if not HINTS_USE_LLM:
        return None
    try:
        prompt = _compose_llm_prompt(deterministic_tips, result)

        # === 在此接入你的LLM客户端 ===
        # 伪代码示例：
        # from openai import OpenAI
        # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # resp = client.chat.completions.create(
        #   model=os.getenv("PFSB_LLM_MODEL", "gpt-4o-mini"),
        #   messages=[{"role":"system","content":"你是严谨的交通策略校验助手。"},
        #             {"role":"user","content":prompt}],
        #   temperature=0.0,
        # )
        # text = resp.choices[0].message.content.strip()

        # 这里先返回模板化占位，确保代码可运行
        text = "\n".join(deterministic_tips[:HINTS_MAX_BULLETS])
        return text
    except Exception:
        return None

def make_hints_payload(result: Dict[str, Any],
                       ir: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    if not HINTS_ENABLE or (result.get("status") != "unsat"):
        return None
    det = suggest_deterministic(result, ir)
    llm_text = generate_llm_hint(det, result)
    return {
        "deterministic": det,
        "llm": llm_text
    }

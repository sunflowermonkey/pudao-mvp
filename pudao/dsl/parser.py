import json
from pathlib import Path
from typing import Any, Dict

import yaml
from jsonschema import validate, Draft7Validator
from pydantic import ValidationError

from .models import StrategyIR
from .id_registry import id_registry


def _load_schema() -> Dict[str, Any]:
    schema_path = Path(__file__).with_name("strategy_schema.json")
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = _load_schema()
VALIDATOR = Draft7Validator(SCHEMA)


def load_raw(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    # 用 utf-8-sig 兼容 BOM
    text = p.read_text(encoding="utf-8-sig").strip()

    # 空文件直接报错，避免 jsonschema 出现 “None is not of type 'object'”
    if not text:
        raise ValueError("schema_violation: empty_or_null_document")

    if p.suffix in [".yaml", ".yml"]:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)

    # 根必须是 object/dict
    if data is None:
        raise ValueError("schema_violation: empty_or_null_document")
    if not isinstance(data, dict):
        raise ValueError(f"schema_violation: root_must_be_object_got_{type(data).__name__}")

    return data


def validate_schema(raw: Dict[str, Any]) -> None:
    # 这里 raw 一定是 dict（上面已保证）
    errors = sorted(VALIDATOR.iter_errors(raw), key=lambda e: e.path)
    if errors:
        # 给出更清晰的路径提示
        msgs = "; ".join([
            (f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}")
            for e in errors
        ])
        raise ValueError(f"schema_violation: {msgs}")


def to_ir(raw: Dict[str, Any]) -> StrategyIR:
    try:
        return StrategyIR.parse_obj(raw)
    except ValidationError as e:
        raise ValueError(f"schema_violation: {e}")


def validate_ids(ir: StrategyIR) -> None:
    # I1: 结构与引用合法性（简化）
    for seg in ir.scope.segments:
        if not id_registry.is_valid_segment(seg):
            raise ValueError(f"invalid_reference: segment {seg}")
    for r in ir.scope.ramps:
        if not id_registry.is_valid_ramp(r):
            raise ValueError(f"invalid_reference: ramp {r}")
    for v in ir.scope.vms:
        if not id_registry.is_valid_vms(v):
            raise ValueError(f"invalid_reference: vms {v}")

    for act in ir.actions:
        if act.type == "vsl" and act.segment_id and not id_registry.is_valid_segment(act.segment_id):
            raise ValueError(f"invalid_reference: segment {act.segment_id}")
        if act.type in ("ramp_metering", "ramp_closure") and act.ramp_id and not id_registry.is_valid_ramp(act.ramp_id):
            raise ValueError(f"invalid_reference: ramp {act.ramp_id}")
        if act.type == "vms_message" and act.vms_id and not id_registry.is_valid_vms(act.vms_id):
            raise ValueError(f"invalid_reference: vms {act.vms_id}")


def load_strategy_ir(path: str) -> StrategyIR:
    raw = load_raw(path)
    validate_schema(raw)
    ir = to_ir(raw)
    validate_ids(ir)
    return ir

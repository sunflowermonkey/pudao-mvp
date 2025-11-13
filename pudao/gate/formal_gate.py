import json
from typing import Dict, Any

from pudao.dsl.parser import load_strategy_ir
from pudao.smt.solver import check_formal_with_smt


def check_formal_file(path: str) -> Dict[str, Any]:
    try:
        ir = load_strategy_ir(path)
    except Exception as e:
        # Schema / ID / 基础错误 → 视作 unsat
        msg = str(e)
        return {
            "allow": False,
            "status": "unsat",
            "reasons": [msg],
            "details": {"I1_structure": "fail"},
        }

    result = check_formal_with_smt(ir)
    return result


def check_formal_file_json(path: str) -> str:
    res = check_formal_file(path)
    return json.dumps(res, ensure_ascii=False, indent=2)

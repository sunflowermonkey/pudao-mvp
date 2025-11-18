# pudao/evidence/evidence.py

"""说明

默认写入到 evidence/formal_timings.ndjson（可用 PFSB_EVIDENCE_FILE 改路径）。

run_id 可用 PFSB_RUN_ID 固定（比如一次 CI 运行一个 ID）。

可用 PFSB_LABEL 给整批测试打标签（如 unit-tests）。"""

import json
import os
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# 环境变量可覆盖输出位置 / 运行批次标识 / 用例标签
EVIDENCE_FILE = os.getenv("PFSB_EVIDENCE_FILE", "evidence/formal_timings.ndjson")
RUN_ID = os.getenv("PFSB_RUN_ID", uuid.uuid4().hex[:12])  # 每进程唯一批次ID
DEFAULT_LABEL = os.getenv("PFSB_LABEL")  # 可选：给整批运行打一个标签

def _iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def _sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def append_raw(record: Dict[str, Any], out_path: Optional[str] = None) -> str:
    """
    直接写入一条 NDJSON 记录；返回文件路径。
    """
    out = Path(out_path or EVIDENCE_FILE)
    _ensure_parent(out)
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(out)

def append_formal_timing(input_path: str, result: Dict[str, Any],
                         label: Optional[str] = None,
                         out_path: Optional[str] = None) -> str:
    """
    将 Formal Gate 的结果（含 timestamps/timings_ms）写入 evidence。
    - input_path: 校验的策略文件路径
    - result: check_formal_file(...) 返回的 dict
    - label: 可选标签（不传则用默认环境变量 PFSB_LABEL）
    - out_path: 可覆写输出文件（默认 EVIDENCE_FILE）
    """
    p = Path(input_path)
    rec = {
        "run_id": RUN_ID,
        "ts_utc": _iso_utc(),
        "label": label or DEFAULT_LABEL,
        "input": {
            "path": str(p),
            "exists": p.exists(),
            "size": (p.stat().st_size if p.exists() else None),
            "sha256": (_sha256_file(p) if p.exists() else None),
        },
        "verdict": {
            "status": result.get("status"),
            "allow": result.get("allow"),
            "reason_top": (result.get("reasons") or [None])[0],
            "details": result.get("details"),
        },
        "timestamps": result.get("timestamps"),
        "timings_ms": result.get("timings_ms"),
    }
    return append_raw(rec, out_path)

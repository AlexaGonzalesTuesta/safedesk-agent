"""Structured traces for every turn, with PII redacted before anything is stored."""
from __future__ import annotations

import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from .guardrails import redact_obj


class Tracer:
    def __init__(self, directory: str | Path | None = None, keep_last: int = 500):
        self.path = None
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.path = Path(directory) / "traces.jsonl"
        self.recent: deque[dict] = deque(maxlen=keep_last)

    def start(self, session_id: str, turn: int, mode: str) -> dict:
        return {
            "trace_id": uuid.uuid4().hex[:16],
            "session_id": session_id,
            "turn": turn,
            "mode": mode,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "_t0": time.perf_counter(),
            "tool_calls": [],
        }

    def finish(self, trace: dict, **fields) -> dict:
        trace.update(fields)
        trace["latency_ms"] = round((time.perf_counter() - trace.pop("_t0")) * 1000, 2)
        record = redact_obj(trace)
        self.recent.append(record)
        if self.path:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def metrics(self) -> dict:
        turns = list(self.recent)
        total = len(turns)
        tool_calls = [c for t in turns for c in t.get("tool_calls", [])]
        blocked = [c for c in tool_calls if not c.get("allowed")]
        escalated = sum(1 for t in turns if t.get("escalated"))
        resolved_by_agent = sum(
            1 for t in turns
            if any(c.get("allowed") and c.get("name") in {"issue_refund", "get_order_status", "update_email", "search_kb"}
                   for c in t.get("tool_calls", []))
            and not t.get("escalated")
        )
        return {
            "turns": total,
            "tool_calls": len(tool_calls),
            "blocked_tool_calls": len(blocked),
            "blocked_by_reason": _count(c.get("reason") for c in blocked),
            "escalations": escalated,
            "turns_resolved_by_agent": resolved_by_agent,
            "prompt_injections_caught": sum(1 for t in turns if t.get("guardrails", {}).get("injection")),
            "security_holds": sum(1 for t in turns if t.get("guardrails", {}).get("security_hold")),
            "intents": _count(t.get("intent") for t in turns),
            "languages": _count(t.get("language") for t in turns),
            "avg_latency_ms": round(sum(t.get("latency_ms", 0) for t in turns) / total, 2) if total else 0,
        }


def _count(values) -> dict:
    out: dict = {}
    for v in values:
        if v is None:
            continue
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))

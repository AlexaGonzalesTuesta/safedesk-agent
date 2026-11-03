"""Support-ops analytics: load agent traces into SQLite and compute KPIs with SQL.

    python -m safedesk analytics --seed     # generate sample traffic, then report
    python -m safedesk analytics            # report on traces/traces.jsonl from real use

This is the "customer zero" loop from docs/customer_zero.md: the traces the agent
already writes become a small analytics table that answers whether the agent is
resolving tickets, where it hands off, and what the policy engine is stopping.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE turns (
    trace_id TEXT PRIMARY KEY,
    session_id TEXT,
    turn INTEGER,
    mode TEXT,
    language TEXT,
    intent TEXT,
    escalated INTEGER,
    injection INTEGER,
    security_hold INTEGER,
    risk_level TEXT,
    latency_ms REAL
);
CREATE TABLE tool_calls (
    trace_id TEXT REFERENCES turns(trace_id),
    seq INTEGER,
    name TEXT,
    allowed INTEGER,
    reason TEXT
);
"""

RESOLVING_TOOLS = "('get_order_status', 'issue_refund', 'update_email', 'search_kb')"

QUERIES: list[tuple[str, str, str]] = [
    (
        "Containment",
        "Share of conversations the agent finished without a human.",
        f"""
WITH s AS (
  SELECT t.session_id,
         MAX(t.escalated) AS escalated,
         MAX(CASE WHEN c.allowed = 1 AND c.name IN {RESOLVING_TOOLS} THEN 1 ELSE 0 END) AS resolved
  FROM turns t LEFT JOIN tool_calls c ON c.trace_id = t.trace_id
  GROUP BY t.session_id
)
SELECT COUNT(*) AS sessions,
       SUM(resolved = 1 AND escalated = 0) AS contained,
       ROUND(100.0 * SUM(resolved = 1 AND escalated = 0) / COUNT(*), 1) AS containment_pct,
       SUM(escalated) AS handed_to_human
FROM s;""",
    ),
    (
        "Handoffs by intent",
        "Which kinds of requests end with a human, and how often.",
        """
SELECT intent,
       COUNT(*) AS turns,
       SUM(escalated) AS handoffs,
       ROUND(100.0 * SUM(escalated) / COUNT(*), 1) AS handoff_pct
FROM turns
GROUP BY intent
ORDER BY handoffs DESC, turns DESC;""",
    ),
    (
        "What the policy engine blocked",
        "Every denied tool call, grouped by the rule that stopped it.",
        """
SELECT reason, name AS tool, COUNT(*) AS blocked
FROM tool_calls
WHERE allowed = 0
GROUP BY reason, name
ORDER BY blocked DESC;""",
    ),
    (
        "Security outcomes",
        "Attacks stopped at the input guardrail or by a security hold.",
        """
SELECT SUM(injection) AS prompt_injections_blocked,
       SUM(security_hold) AS security_holds,
       SUM(risk_level = 'high') AS high_risk_turns,
       (SELECT COUNT(*) FROM tool_calls
         WHERE name = 'issue_refund' AND allowed = 1
           AND trace_id IN (SELECT trace_id FROM turns WHERE risk_level = 'high')) AS refunds_in_high_risk_turns
FROM turns;""",
    ),
    (
        "Language parity",
        "Do Spanish speakers get resolved at the same rate as English speakers?",
        f"""
WITH s AS (
  SELECT t.session_id,
         MAX(t.language) AS language,
         MAX(t.escalated) AS escalated,
         MAX(CASE WHEN c.allowed = 1 AND c.name IN {RESOLVING_TOOLS} THEN 1 ELSE 0 END) AS resolved
  FROM turns t LEFT JOIN tool_calls c ON c.trace_id = t.trace_id
  GROUP BY t.session_id
)
SELECT language,
       COUNT(*) AS sessions,
       ROUND(100.0 * SUM(resolved = 1 AND escalated = 0) / COUNT(*), 1) AS containment_pct
FROM s
GROUP BY language;""",
    ),
    (
        "Tool reliability and latency",
        "How often each tool runs, how often it is allowed, and turn latency.",
        """
SELECT c.name AS tool,
       COUNT(*) AS calls,
       ROUND(100.0 * AVG(c.allowed), 1) AS allowed_pct,
       ROUND(AVG(t.latency_ms), 2) AS avg_turn_latency_ms
FROM tool_calls c JOIN turns t ON t.trace_id = c.trace_id
GROUP BY c.name
ORDER BY calls DESC;""",
    ),
]


def load(trace_file: Path, db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript("DROP TABLE IF EXISTS tool_calls; DROP TABLE IF EXISTS turns;" + SCHEMA)
    with trace_file.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            t = json.loads(line)
            g = t.get("guardrails", {})
            conn.execute(
                "INSERT OR REPLACE INTO turns VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    t["trace_id"], t["session_id"], t["turn"], t.get("mode"), t.get("language"), t.get("intent"),
                    int(bool(t.get("escalated"))), int(bool(g.get("injection"))), int(bool(g.get("security_hold"))),
                    g.get("risk_level", "low"), t.get("latency_ms", 0.0),
                ),
            )
            for i, c in enumerate(t.get("tool_calls", []), start=1):
                conn.execute(
                    "INSERT INTO tool_calls VALUES (?,?,?,?,?)",
                    (t["trace_id"], i, c["name"], int(bool(c["allowed"])), c["reason"]),
                )
    conn.commit()
    return conn


def seed(trace_dir: Path) -> Path:
    """Replay the eval conversations plus the demo script to produce realistic traffic."""
    from .agent import SupportAgent
    from .config import TenantConfig, REPO_DIR
    from .store import Store
    from .tracing import Tracer

    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_file = trace_dir / "traces.jsonl"
    if trace_file.exists():
        trace_file.unlink()
    tenant = TenantConfig.load()
    tracer = Tracer(trace_dir)
    cases_file = REPO_DIR / "evals" / "cases.jsonl"
    for line in cases_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        agent = SupportAgent(store=Store(), tenant=tenant, tracer=tracer)
        session = agent.new_session()
        for turn in case["turns"]:
            agent.handle(session, turn)
    return trace_file


def _table(cursor) -> str:
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join(out)


def report(conn: sqlite3.Connection, source: str) -> str:
    parts = [
        "# SafeDesk support KPIs",
        "",
        f"Source: `{source}`, loaded into SQLite (tables `turns` and `tool_calls`). Every number below comes from the SQL shown with it.",
        "",
    ]
    for title, question, sql in QUERIES:
        cur = conn.execute(sql)
        parts += [f"## {title}", "", question, "", "```sql" + sql + "\n```", "", _table(cur), ""]
    return "\n".join(parts)


def main(trace_path: str | None = None, seed_first: bool = False, out: str | None = None) -> int:
    from .config import REPO_DIR

    out = out or str(REPO_DIR / "reports" / "kpi_report.md")
    trace_file = Path(trace_path or "traces/traces.jsonl")
    if seed_first:
        trace_file = seed(trace_file.parent)
    if not trace_file.exists():
        print(f"No traces at {trace_file}. Chat with the agent first, or run: python -m safedesk analytics --seed")
        return 1
    conn = load(trace_file)
    text = report(conn, str(trace_file).replace("\\", "/"))
    print(text)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text + "\n", encoding="utf-8")
        print(f"\nwrote {Path(out).relative_to(REPO_DIR) if Path(out).is_relative_to(REPO_DIR) else out}")
    return 0

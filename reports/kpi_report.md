# SafeDesk support KPIs

Source: `traces/traces.jsonl`, loaded into SQLite (tables `turns` and `tool_calls`). Every number below comes from the SQL shown with it.

## Containment

Share of conversations the agent finished without a human.

```sql
WITH s AS (
  SELECT t.session_id,
         MAX(t.escalated) AS escalated,
         MAX(CASE WHEN c.allowed = 1 AND c.name IN ('get_order_status', 'issue_refund', 'update_email', 'search_kb') THEN 1 ELSE 0 END) AS resolved
  FROM turns t LEFT JOIN tool_calls c ON c.trace_id = t.trace_id
  GROUP BY t.session_id
)
SELECT COUNT(*) AS sessions,
       SUM(resolved = 1 AND escalated = 0) AS contained,
       ROUND(100.0 * SUM(resolved = 1 AND escalated = 0) / COUNT(*), 1) AS containment_pct,
       SUM(escalated) AS handed_to_human
FROM s;
```

| sessions | contained | containment_pct | handed_to_human |
|---|---|---|---|
| 34 | 16 | 47.1 | 9 |

## Handoffs by intent

Which kinds of requests end with a human, and how often.

```sql
SELECT intent,
       COUNT(*) AS turns,
       SUM(escalated) AS handoffs,
       ROUND(100.0 * SUM(escalated) / COUNT(*), 1) AS handoff_pct
FROM turns
GROUP BY intent
ORDER BY handoffs DESC, turns DESC;
```

| intent | turns | handoffs | handoff_pct |
|---|---|---|---|
| refund | 16 | 5 | 31.3 |
| human | 2 | 2 | 100.0 |
| provide_identity | 4 | 1 | 25.0 |
| update_email | 4 | 1 | 25.0 |
| order_status | 9 | 0 | 0.0 |
| kb | 6 | 0 | 0.0 |
| greeting | 3 | 0 | 0.0 |
| prompt_injection | 3 | 0 | 0.0 |
| unknown | 1 | 0 | 0.0 |

## What the policy engine blocked

Every denied tool call, grouped by the rule that stopped it.

```sql
SELECT reason, name AS tool, COUNT(*) AS blocked
FROM tool_calls
WHERE allowed = 0
GROUP BY reason, name
ORDER BY blocked DESC;
```

| reason | tool | blocked |
|---|---|---|
| order_not_owned_by_verified_customer | get_order_status | 1 |
| verification_locked | verify_identity | 1 |

## Security outcomes

Attacks stopped at the input guardrail or by a security hold.

```sql
SELECT SUM(injection) AS prompt_injections_blocked,
       SUM(security_hold) AS security_holds,
       SUM(risk_level = 'high') AS high_risk_turns,
       (SELECT COUNT(*) FROM tool_calls
         WHERE name = 'issue_refund' AND allowed = 1
           AND trace_id IN (SELECT trace_id FROM turns WHERE risk_level = 'high')) AS refunds_in_high_risk_turns
FROM turns;
```

| prompt_injections_blocked | security_holds | high_risk_turns | refunds_in_high_risk_turns |
|---|---|---|---|
| 3 | 5 | 5 | 0 |

## Language parity

Do Spanish speakers get resolved at the same rate as English speakers?

```sql
WITH s AS (
  SELECT t.session_id,
         MAX(t.language) AS language,
         MAX(t.escalated) AS escalated,
         MAX(CASE WHEN c.allowed = 1 AND c.name IN ('get_order_status', 'issue_refund', 'update_email', 'search_kb') THEN 1 ELSE 0 END) AS resolved
  FROM turns t LEFT JOIN tool_calls c ON c.trace_id = t.trace_id
  GROUP BY t.session_id
)
SELECT language,
       COUNT(*) AS sessions,
       ROUND(100.0 * SUM(resolved = 1 AND escalated = 0) / COUNT(*), 1) AS containment_pct
FROM s
GROUP BY language;
```

| language | sessions | containment_pct |
|---|---|---|
| en | 25 | 44.0 |
| es | 9 | 55.6 |

## Tool reliability and latency

How often each tool runs, how often it is allowed, and turn latency.

```sql
SELECT c.name AS tool,
       COUNT(*) AS calls,
       ROUND(100.0 * AVG(c.allowed), 1) AS allowed_pct,
       ROUND(AVG(t.latency_ms), 2) AS avg_turn_latency_ms
FROM tool_calls c JOIN turns t ON t.trace_id = c.trace_id
GROUP BY c.name
ORDER BY calls DESC;
```

| tool | calls | allowed_pct | avg_turn_latency_ms |
|---|---|---|---|
| verify_identity | 20 | 95.0 | 0.76 |
| check_refund_eligibility | 10 | 100.0 | 0.39 |
| escalate_to_human | 9 | 100.0 | 0.37 |
| create_case | 9 | 100.0 | 0.37 |
| search_kb | 6 | 100.0 | 0.73 |
| get_order_status | 6 | 83.3 | 1.57 |
| issue_refund | 5 | 100.0 | 0.4 |
| update_email | 1 | 100.0 | 0.25 |


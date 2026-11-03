from safedesk.analytics import QUERIES, load, seed


def test_seeded_traces_load_into_sql_and_kpis_hold(tmp_path):
    trace_file = seed(tmp_path)
    conn = load(trace_file)
    turns = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    assert turns > 30
    # No refund was ever allowed in a high-risk turn.
    unsafe = conn.execute(
        "SELECT COUNT(*) FROM tool_calls c JOIN turns t ON t.trace_id = c.trace_id "
        "WHERE c.name = 'issue_refund' AND c.allowed = 1 AND t.risk_level = 'high'"
    ).fetchone()[0]
    assert unsafe == 0
    # Every report query runs.
    for _, _, sql in QUERIES:
        conn.execute(sql).fetchall()

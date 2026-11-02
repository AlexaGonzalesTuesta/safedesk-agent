# Deployment playbook: taking SafeDesk to a new customer

This is how a forward deployed engineer would stand SafeDesk up for a new customer in about two weeks, from kickoff to a limited pilot.

## Week 1: discover and configure

### Day 1: discovery workshop
Ask the customer's support lead and security lead:
* What are your top ten ticket types by volume? Which are routine?
* What is your refund policy (window, final sale rules, who approves large refunds)?
* What counts as proof of identity today on the phone and in chat?
* Which languages do your customers use?
* Where should escalations go, and what is the SLA?

### Day 2: write the tenant config
Copy `tenants/northwind_outfitters.json` and fill in the answers:

```json
{
  "tenant_id": "customer-name",
  "brand_name": "Customer Name",
  "refund_window_days": 30,
  "auto_refund_limit": 500.0,
  "supported_languages": ["en", "es"],
  "escalation_queue": "Tier 2 Support",
  "escalation_sla": {"en": "4 business hours", "es": "4 horas hábiles"},
  "max_verification_attempts": 3
}
```

Run with it: `python -m safedesk chat --tenant customer_name.json`. No code changes.

### Days 3 and 4: connect data
Replace the seed files in `safedesk/data/` with a read-only export or an adapter to the customer's order system. The store needs four lookups: order by id, customer by id, refund ledger write, case write. Load their help center articles into `kb.json`.

### Day 5: customer-specific evals
Add 20 to 30 cases to `evals/cases.jsonl` from the customer's real (anonymized) transcripts, including at least five attacks they have actually seen. Run `python evals/run_evals.py --tenant customer_name.json`. Do not move on until unsafe actions are zero.

## Week 2: test and pilot

### Days 6 and 7: user acceptance testing
Support specialists use the web console for a day. Every reply they disagree with becomes a new eval case. The trace panel shows them why the agent did what it did, which is what builds their trust.

### Day 8: security review
Walk the customer's security team through `policy.py`. Show the test that proves a model cannot refund without verification. Agree on the auto-approval limit.

### Days 9 and 10: limited pilot
Route 10% of chats in one channel to SafeDesk. Watch `/metrics` daily: containment, escalations, blocked calls, false positive complaints.

## Go-live checklist

- [ ] Tenant config reviewed by support lead and security lead
- [ ] Customer-specific eval cases added, unsafe action rate 0%
- [ ] Escalation queue receives test cases with summaries
- [ ] Traces confirmed free of PII
- [ ] Rollback plan: one config flag routes all chats back to humans
- [ ] Weekly review owner named (see customer_zero.md)

## Rollback

Set the channel routing back to the human queue. Because the agent only acts through the policy engine and logs every call, any action it took during the pilot can be found in the trace log by session id.

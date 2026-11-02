# Architecture

## Request lifecycle

1. **Language detection** (`language.py`). Marker-word scoring plus Spanish punctuation and accents. Messages that are only an order number or email keep the session's language.
2. **Input guardrails** (`guardrails.py`).
   * Prompt injection: regex patterns in English and Spanish. A match short-circuits the turn. The planner never sees the message.
   * Social engineering: five signal categories (impersonation, urgency, verification bypass, payout redirect, synthetic media). Categories accumulate on the session. Two or more categories, or any bypass attempt, is high risk.
3. **Planning** (`agent.py`).
   * Rules mode: intent classification, entity extraction (order ids, emails), and a multi-turn state machine for verification.
   * Claude mode: the Messages API with tool use. Tool schemas come from the same registry.
4. **Execution** (`SupportAgent.execute_tool`). The single entry point to any tool. It calls `PolicyEngine.check` first.
5. **Policy** (`policy.py`). Checks, in order:
   * verification lockout after N failed attempts
   * identity verified before any account tool
   * the order belongs to the verified customer
   * high risk blocks refunds and email changes, and medium risk blocks email changes
   * refund eligibility (delivered, not final sale, inside the window, not already refunded) and the auto-approval limit
6. **Reply** (`responder.py` in rules mode, the model in Claude mode).
7. **Trace** (`tracing.py`). Intent, language, guardrail results, every tool call with allowed or blocked and the reason, latency. Redacted before writing.

## Why a denial goes back to the planner

When the policy engine blocks a call, the planner receives a structured result: `{"error": "blocked_by_policy", "policy_reason": "...", "route_to_human": true}`. In Claude mode the model reads that and explains it to the customer. That means the model's freedom is in how it talks, not in what it is allowed to do.

## Data model

* `customers.json`: id, name, email, zip, preferred language
* `orders.json`: id, customer id, status, carrier, ETA, delivered date, final sale flag, refunded flag, items with prices
* `kb.json`: policy articles with English and Spanish keywords, titles, and answers
* Runtime ledgers on the Store: refunds, cases, email changes

## Testing strategy

| Layer | Where |
|---|---|
| Guardrail patterns and redaction | `tests/test_guardrails.py` |
| Policy rules and tenant config | `tests/test_policy.py` |
| Flows, ledger effects, traces, Claude mode with a scripted fake client | `tests/test_agent.py` |
| HTTP API and console | `tests/test_api.py` |
| End-to-end conversations, safety metrics | `evals/run_evals.py` |

CI (`.github/workflows/ci.yml`) runs tests and evals on every push and fails the build if any unsafe action succeeds.

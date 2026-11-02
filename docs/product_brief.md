# Product brief: SafeDesk

## Problem

Support teams want AI agents to resolve tickets end to end, not just draft replies. The blocker is trust. An agent that can issue refunds and change account emails is also an agent that a scammer can talk into doing those things. Voice cloning and impersonation make this worse: "I'm the account owner, here's a voice note" is now a cheap attack.

## Users

| User | Need |
|---|---|
| Customer | Fast answers in their language, refunds without waiting in a queue |
| Support specialist | Only the cases that need judgment, with context already gathered |
| Support operations lead | Proof the agent is resolving tickets safely, and where it is not |
| Security and compliance | Assurance that no account action happens without verification, and an audit trail |

## Goals and success metrics

| Goal | Metric | Target for pilot |
|---|---|---|
| Resolve routine tickets | Share of conversations resolved without a human (containment) | 60% or more |
| Never take an unsafe action | Unsafe action rate on the adversarial eval suite | 0% |
| Catch attacks | Guardrail recall on adversarial cases | 95% or more |
| Do not punish real customers | Guardrail false positive rate on benign cases | under 5% |
| Serve Spanish speakers | Pass rate on Spanish cases | equal to English |
| Hand off cleanly | Escalations with a case already opened and summarized | 100% |

## Scope for v0.1

In: order status, refunds with policy checks and an auto-approval limit, email change, policy questions, human handoff, English and Spanish, prompt injection and social engineering screening, redacted traces, metrics, tenant configs, eval suite.

Out: payments changes, address changes, password resets in chat, voice channel, real CRM connector.

## Key decisions and tradeoffs

1. **Policy in code, not in the prompt.** Prompts can be argued with; a function that checks verification and ownership cannot. Tradeoff: every new action needs a policy rule written and tested.
2. **Risk accumulates per session.** Attackers split a request across messages. Tracking signals per session catches that. Tradeoff: one suspicious remark early in a chat makes later account changes go to a human.
3. **Urgency alone is not an attack.** Real customers are often in a hurry. Requiring two signals (or a verification bypass attempt) for a hold keeps false positives at zero on the current suite.
4. **Over-limit refunds go to people.** The auto-approval limit is per tenant, so finance teams decide their own risk tolerance.
5. **Deterministic baseline plus LLM.** The rules planner gives a reproducible baseline and runs with no API cost. The Claude planner handles open-ended language. Both are graded by the same evals.

## Roadmap

1. Run the eval suite in Claude mode and compare containment and safety against rules mode.
2. Add 50 more adversarial cases from real attack patterns (gift cards, SIM swap stories, fake executives).
3. CRM adapter interface so the store can be swapped for Salesforce Service Cloud or Zendesk.
4. Human review queue for security holds, with one-click approve or reject that feeds back into the eval set.

# SafeDesk Agent

**A customer-service AI agent that can issue refunds and change accounts, and that still can't be talked into moving money by a scammer, a prompt injection, or its own mistakes.** English and Spanish.

![tests](https://img.shields.io/badge/tests-26%20passing-brightgreen) ![evals](https://img.shields.io/badge/evals-34%2F34-brightgreen) ![unsafe actions](https://img.shields.io/badge/unsafe%20actions-0-brightgreen) ![python](https://img.shields.io/badge/python-3.9%2B-blue)

![SafeDesk Case Desk demo: a refund from the test accounts, a "fraud team" gift card scam stopped, a slow-burn voice-note attack stopped, and a cross-account lookup denied](docs/demo.gif)

### [Try the live demo](https://safedesk-agent.onrender.com)

No sign-up, no API key, fictional data only. Each visitor gets a private sandbox. On the free tier the first visit can take about a minute to wake up.

## Why this exists

Companies want AI agents that resolve support tickets end to end, which means giving them real permissions: issuing refunds, changing account details. That makes the agent a fraud target. Voice cloning and impersonation are now cheap (I built deepfakes professionally for a security awareness service), and most agent demos rely on the system prompt to say no. A prompt can be argued with.

SafeDesk puts every rule in code that sits between the model and the account, then proves it with adversarial tests that fail the build if a single unsafe action gets through.

## What's different from a typical agent demo

* **Safety is measured, not claimed.** 34 scripted conversations, 10 of them attacks, run on every push. The build fails if any refund or account change slips through, and it also tracks how often a legitimate customer gets wrongly blocked.
* **The model cannot bypass the rules.** A test scripts an LLM that tries to refund an unverified customer. The policy engine blocks it and no money moves.
* **The attacks are realistic.** Impersonation, "skip verification," gift card redirects, voice-note claims, and attacks spread across several messages, in English and Spanish.
* **It is built like a product.** Handoffs to humans, per-customer configuration, redacted logs, SQL analytics on those logs, a product brief, and a rollout plan.

## The 2-minute tour

1. **Open the [live demo](https://safedesk-agent.onrender.com)** (or run it locally, below).
2. **Press `4`.** A "fraud team" asks for a gift card refund. Four risk signals light up, no account tool is ever called, and a specialist gets a high priority case.
3. **Press `5`.** The same trick split across two messages, with the correct email. Still blocked, because risk adds up over the session.
4. **Open Test accounts** on the left and click **Refund** on order A1002. A real customer gets their $129 back in one message.
5. **Read the Decision ledger** on the right. Every tool call shows ALLOW or DENY and the policy rule behind it.

Fifteen guided scenarios, with exact messages to type and the expected result for each, are in **[docs/TRY_IT.md](docs/TRY_IT.md)**.

## Results

| | |
|---|---|
| Eval conversations passed | **34 / 34** (10 adversarial, 6 in Spanish), [report](reports/eval_report.md) |
| Unsafe actions on adversarial cases | **0** |
| Attacks caught (guardrail recall) | **100%** |
| Legitimate customers wrongly blocked | **0%** |
| Unit, policy, API, and analytics tests | **26 passing**, in CI on Python 3.10 and 3.12 (also runs on 3.9) |
| Support KPIs computed in SQL from agent traces | [reports/kpi_report.md](reports/kpi_report.md) |

The rule-based planner was built alongside the eval cases, so the 100% shows the flows and the policy layer work as designed. The harder test is `python evals/run_evals.py --mode claude`, where an LLM does the planning and the policy layer has to hold. The KPI report is generated from the eval conversations, which are mostly attacks, so its containment rate is lower than real traffic would produce.

## Test accounts

All fictional. The demo runs as if today is 2026-11-02. Verify with an order number plus the email on that row.

| Order | Email | Item | What a refund request does |
|---|---|---|---|
| A1001 | `ana.ruiz@example.com` | Wireless headset, $89, shipped | Refused, not delivered yet |
| A1002 | `ana.ruiz@example.com` | Rain jacket, $129, delivered | **Approved automatically** |
| A1003 | `marcus.lee@example.com` | Bottle and cap, $59, delivered 48 days ago | Refused, outside the 30-day window |
| A1004 | `marcus.lee@example.com` | Tent, $899, delivered | Sent to a human, above the $500 limit |
| A1005 | `priya.shah@example.com` | Clearance socks, $45, delivered | Refused, final sale |
| A1006 | `priya.shah@example.com` | Hiking boots, $240, processing | Refused, not delivered yet |

Try: `Where is my order A1001? My email is ana.ruiz@example.com`

## How it works

```mermaid
flowchart LR
    U[Customer message] --> L[Language detection]
    L --> G[Input guardrails<br/>prompt injection<br/>social engineering risk]
    G -->|blocked| R[Safe reply]
    G --> P{Planner}
    P -->|rules mode| RB[Deterministic planner]
    P -->|claude mode| C[Claude with tool use]
    RB --> X[execute_tool]
    C --> X
    X --> PE[Policy engine<br/>identity, ownership,<br/>refund rules, risk level]
    PE -->|allowed| T[Tools: orders, refunds,<br/>email, KB, cases]
    PE -->|denied| D[Denial returned to planner<br/>plus human handoff when needed]
    T --> TR[Redacted trace]
    D --> TR
    TR --> SQL[SQLite KPIs]
```

**The key decision: rules live in code, not in the prompt.** Every tool call from either planner goes through one function, `execute_tool`, which asks the policy engine first. The policy checks that the customer is verified, that the order is theirs, that the refund meets policy and the auto-approval limit, and that the session isn't high risk. A prompt can be argued with; that function can't. `tests/test_agent.py::test_llm_cannot_refund_without_verification` scripts a model that tries to refund an unverified customer and confirms the refund never happens.

Other decisions and their tradeoffs:

| Decision | Why | Tradeoff |
|---|---|---|
| Risk accumulates per session | Attackers split requests across messages | One suspicious remark sends later account changes to a human |
| Urgency alone is only medium risk | Real customers are often in a hurry | A one-signal attack on a refund is caught only by verification |
| Over-limit refunds go to people | Finance sets risk tolerance per customer, in config | More handoffs for high-value orders |
| Two planners, one policy layer | Deterministic baseline with no API cost, LLM for open-ended language | Two code paths to keep in sync |
| PII masked before logging | Traces are safe to analyze and share | Debugging needs the original session |
| Tenants are JSON files | A new customer is a config change, not a code change | Business rules beyond these fields still need code |

## Run it on your own computer

The live demo needs nothing installed. To run it yourself, you need Python 3.9 or newer. The local console runs only on your machine at `http://127.0.0.1:8000`.

```bash
git clone https://github.com/AlexaGonzalesTuesta/safedesk-agent.git
cd safedesk-agent
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements-dev.txt
```

| Command | What it does |
|---|---|
| `uvicorn safedesk.api:app --reload` | Case Desk console at http://127.0.0.1:8000 |
| `python -m safedesk demo` | Six scripted conversations in the terminal |
| `python -m safedesk chat` | Chat with the agent in the terminal |
| `python -m pytest -q` | 26 tests |
| `python evals/run_evals.py` | 34-conversation eval suite, writes `reports/eval_report.md` |
| `python -m safedesk analytics --seed` | Loads agent traces into SQLite and writes `reports/kpi_report.md` |
| `python -m safedesk chat --tenant andes_coffee_co.json` | Second customer config: 14-day window, $150 limit |

**With Claude (optional):** `pip install anthropic`, set `ANTHROPIC_API_KEY` and `SAFEDESK_MODE=claude`, then use any command above. Tools, policy, traces, and evals stay the same.

**Deploy your own copy (free):** on [Render](https://render.com), choose New, then Blueprint, then pick this repo. `render.yaml` sets everything up. Docker also works: `docker build -t safedesk . && docker run -p 8000:8000 safedesk`.

**About the public demo's safety:** it runs in rules mode with no API key, so there is nothing to leak and no usage bill. All customers, emails, and orders are fictional. Each browser gets its own sandbox (data, sessions, and results), so one visitor can't see or reset another's. Messages are capped at 2,000 characters and logs mask emails, card numbers, and phone numbers.

## The Case Desk console

Built for the people who would supervise this agent: support specialists and support-ops leads who already spend their day in a case console. It reads like a case file plus an audit log, not a chat app. The top strip says what to try and keeps three numbers for your sandbox: attacks stopped, customers helped, and conversations sent to a human.

* **Cases and Test accounts** (left): eleven replayable cases (keys `1` to `0` open the first ten), and every fictional order with Track and Refund buttons.
* **Case file** (center): the transcript with identity status, language, risk, and what the agent is waiting on.
* **Decision ledger** (right): session risk signals as a checklist, then every tool call with its verdict and reason. Hover a transcript entry to highlight its rows.

Empty, loading, validation, and offline states are handled. Type is Atkinson Hyperlegible for long reading shifts and IBM Plex Mono for IDs and figures.

API: `POST /chat`, `GET /demo-data`, `GET /traces`, `GET /metrics`, `GET /sessions/{id}`, `POST /reset`, `GET /health`.

## How the project covers the AI product lifecycle

| Stage | What it shows | Where |
|---|---|---|
| Build | Agent, tool registry, policy engine, API, console, tests, CI, Docker, deploy config | `safedesk/`, `tests/`, `.github/workflows/ci.yml`, `render.yaml` |
| Shape | Users, success metrics with targets, scope, decisions, roadmap | [docs/product_brief.md](docs/product_brief.md) |
| Deliver | Rolling it out to a new customer in two weeks, tenant configs, go-live checklist | [docs/deployment_playbook.md](docs/deployment_playbook.md), `tenants/` |
| Transform | Running it on ourselves: SQL KPIs over traces, weekly review loop | [docs/customer_zero.md](docs/customer_zero.md), [reports/kpi_report.md](reports/kpi_report.md) |
| Evaluate | Multi-turn evals with safety metrics that fail the build | `evals/`, [reports/eval_report.md](reports/eval_report.md) |

## Limitations and next steps

* **Keyword risk signals are a floor, not a ceiling.** A paraphrased attack that avoids every phrase gets through to verification, which still has to pass. Next: a small classifier trained on labeled attack transcripts, keeping the keyword rules underneath.
* **Claude mode has unit tests with a scripted model, not a published eval run.** Next: run the 34 cases against Claude and compare containment and safety with rules mode.
* **The store is in memory.** Next: an adapter interface for a real CRM such as Salesforce Service Cloud or Zendesk.
* **Security holds land in a case list.** Next: a review queue where a specialist approves or rejects, and each decision becomes a new eval case.

## How I built it

I designed the system, the policy rules, and the eval cases, and I used Claude as an AI pair programmer to write and test the code faster. Every behavior described here is covered by a test or an eval that runs in CI.

## Why I built this

During my internship at Reveal Risk I worked on a deepfake-awareness service, training face-swap and voice-cloning models to show companies how convincing impersonation has become. At the same time, everyone wants AI agents that can act on customer accounts. Put those together and the obvious question is what happens when someone sends that agent a cloned voice note and asks for a refund to a different card. SafeDesk is my answer: let the model talk, but make the rules that protect the account impossible to talk around.

Alexa Gonzales Tuesta, Purdue University (Business Analytics and Information Management, Computer Science minor).

License: MIT

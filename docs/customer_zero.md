# Customer zero: running SafeDesk on ourselves

Before selling an agent, use it internally and let the data tell you what to fix. This is the operating rhythm I would use.

## What we measure

Everything comes from the redacted traces (`traces/traces.jsonl`) and the `/metrics` endpoint.

| Metric | Question it answers |
|---|---|
| Containment (turns resolved by the agent with no escalation) | Is the agent actually saving specialist time? |
| Escalations by reason | Which handoffs are policy (over limit, security) and which are the agent failing to understand? |
| Blocked tool calls by reason | Is the policy engine stopping real attacks, or blocking legitimate customers? |
| Security holds | How often are we seeing social engineering, and what patterns? |
| Language mix | Are Spanish speakers resolved at the same rate as English speakers? |

## Weekly review (30 minutes)

1. Pull the ten escalations with reason `customer_requested_human` and read the transcripts. If a pattern repeats, it is a candidate for a new tool or flow.
2. Pull every security hold. Confirm each was a real attack or mark it as a false positive. False positives become benign eval cases; real attacks become adversarial eval cases.
3. Re-run `python evals/run_evals.py`. The suite only grows.
4. Pick one improvement for the next week and write down the metric it should move.

## Estimating value

```
hours saved per week = contained conversations x average handle time saved / 60
```

At 2,000 chats a week, 60% containment, and 6 minutes saved per contained chat, that is 120 specialist hours a week. Those hours go to the cases that need judgment, which are the ones the agent already summarized and escalated.

## Feedback loop

Specialists can flag any agent reply in the console. Each flag becomes an eval case with the corrected expectation. That turns day-to-day support work into training and test data without a separate labeling project.

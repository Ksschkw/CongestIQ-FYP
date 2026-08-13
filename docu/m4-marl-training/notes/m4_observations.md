# M4 Observations: Single‑Agent Fix and Early MARL Preparation

**Author:** Okafor Kosisochukwu Johnpaul  
**Date:** 13 August 2026

---

## What I Observed

### Single‑Agent Throughput Finally Improved

After fixing two critical bugs (observation throughput and action application), my RL agent's performance changed dramatically:

| Metric      | Before fix (M3) | After fix (M4 v2) |
|-------------|-----------------|--------------------|
| Throughput  | 209 kbps        | **8565 kbps**      |
| Delay       | 22.81 ms        | 85.67 ms           |
| Loss        | 0.00%           | 0.34%              |

Throughput increased by **40×**. The agent can now actually control cwnd and use the bottleneck.

---

## The Tradeoff

The agent learned to be **aggressive**: it keeps the queue full to maximise throughput. This causes:

- Higher queueing delay (85.67 ms vs 62.78 ms for CUBIC in M2)
- Slightly more packet loss (0.34% vs 0.19%)

This is the classic throughput–delay tradeoff. My reward function v2 heavily rewarded throughput, so the agent optimised for that.

For a single bulk transfer, this is fine. But in a multi‑agent setting, this aggression could starve other flows.

---

## Why This Happened

The reward function v2 gives:

- +20 for full throughput
- -1 per 10 ms of queueing delay
- -0.2 per 1% loss

A small amount of delay and loss is worth it for more throughput. The agent correctly learned to keep cwnd high.

---

## What I Need To Change For MARL

- [ ] Add a fairness term (e.g., reward sharing the bottleneck equally)
- [ ] Penalise aggressive behaviour when multiple agents compete
- [ ] Tune weights to balance throughput, delay, loss, and fairness

---

## Placeholders for Multi‑Agent Observations

### After MARL training
[TO BE FILLED]
- Did the agents learn to share fairly?
- What fairness index did they achieve?
- Did delay improve compared to single‑agent?
- Did throughput stay high while fairness increased?

### Key Insights
[TO BE FILLED]

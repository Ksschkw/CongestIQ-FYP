# M4 Observations: Single‑Agent Fix and MARL Results

**Author:** Okafor Kosisochukwu Johnpaul  
**Date:** 15 August 2026

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

The single agent learned to be **aggressive**: it keeps the queue full to maximise throughput. This causes:

- Higher queueing delay (85.67 ms vs 62.78 ms for CUBIC in M2)
- Slightly more packet loss (0.34% vs 0.19%)

This is the classic throughput–delay tradeoff. My reward function v2 heavily rewarded throughput, so the agent optimised for that.

---

## Multi‑Agent Results

After implementing CTDE with a fairness reward, the two RL agents achieved:

| Metric      | MARL Agent 1 | MARL Agent 2 |
|-------------|--------------|--------------|
| Throughput  | 5112.1 kbps  | 4824.8 kbps  |
| Delay       | 60.96 ms     | 60.80 ms     |
| Loss        | 0.04%        | 0.05%        |

**Jain Fairness Index: 0.9992**  
**Total throughput: 9936.9 kbps (99.37% of bottleneck)**

---

## What I Learned

1. **Environment correctness is the foundation.** The biggest gains came from fixing bugs, not tuning rewards.
2. **Fairness reward works.** The two agents shared almost perfectly.
3. **CTDE is effective.** One shared policy can learn cooperative behaviour.
4. **Observation normalisation matters.** Without scaling, PPO produced NaNs.
5. **MARL is feasible in simulation.** Despite long training times, the result is excellent.

---

## Key Insights

- The M3 failure was not an RL problem; it was a broken observation and action bug.
- Once fixed, a single agent could saturate the bottleneck.
- Adding a fairness term transformed greedy single‑agent behaviour into cooperative multi‑agent sharing.
- The final MARL result outperforms CUBIC in fairness and total throughput while keeping similar delay and very low loss.
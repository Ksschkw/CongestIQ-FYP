# M4 Experiment Log: From Broken Single‑Agent to MARL

**Author:** Okafor Kosisochukwu Johnpaul  
**Date:** 13 August 2026

---

## Experiment 1: Fix Throughput Observation

**Problem:** RL agent saw throughput as zero most steps.

**Cause:** Throughput was computed from `bytesInFlight` snapshots instead of delivered bytes.

**Fix:** Use `PacketSink::GetTotalRx()` delta between steps.

**Result:** Debug output showed real throughput values (e.g., 428800 bps, 257280 bps).

---

## Experiment 2: Fix Action Application

**Problem:** cwnd stayed around 800–1200 bytes despite repeated "increase" actions.

**Cause:** Action code stored an absolute value (`mult * 1000`) instead of the multiplier itself.

**Fix:** Store the multiplier and apply `newCwnd = currentCwnd * multiplier`.

**Result:** Training reward became positive, and evaluation throughput jumped from 209 kbps to 8565 kbps.

---

## Experiment 3: Reward Function v2

**Formula:**

```
throughput_reward = min(throughput_mbps / 10, 1.0) * 20
delay_penalty = queueing_delay_ms / 10
loss_penalty = loss_rate * 20
reward = throughput_reward - delay_penalty - loss_penalty
```

**Training:** 100,000 timesteps, ~49 PPO iterations.

**Training reward progression:**  
- Start: -8490  
- End: +4840

**Evaluation:**  
- Throughput: 8565.3 kbps  
- Delay: 85.67 ms  
- Loss: 0.34%

---

## Experiment 4: Multi‑Agent Training (Planned)

[TO BE FILLED]
- Number of agents: ____
- Reward wrapper with fairness: ____
- Training duration: ____
- Convergence results: ____

---

## Bugs Found and Fixed

| Bug | Location | Impact | Fix |
|-----|----------|--------|-----|
| Fake throughput observation | `marl-rl-env.cc` `GetObservation()` | Agent couldn't see real throughput | Use PacketSink RX bytes |
| Action set absolute cwnd | `marl-rl-env.cc` `ExecuteActions()` | cwnd never grew | Store multiplier, apply in `IncreaseWindow()` |

---

## Files Modified

- `marl-rl-env.h` – added `m_actionMultiplier` and `m_lastRxBytes`
- `marl-rl-env.cc` – fixed observation and action logic
- `reward_wrapper_m4.py` – first reward attempt
- `reward_wrapper_m4v2.py` – second reward, heavily throughput‑weighted
- `train_m4_single.py`, `train_m4_single_v2.py` – training scripts
- `eval_m4_single.py`, `eval_m4_single_v2.py` – evaluation scripts
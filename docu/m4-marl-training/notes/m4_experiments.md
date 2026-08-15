# M4 Experiment Log: From Broken Single‑Agent to MARL

**Author:** Okafor Kosisochukwu Johnpaul  
**Date:** 15 August 2026

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

## Experiment 4: Multi‑Agent Environment (Option A / CTDE)

**Objective:** Train a single shared PPO policy that controls two RL flows on the same bottleneck.

**Observation:** 8 numbers (cwnd, RTT, loss, throughput for each flow).  
**Action:** 2 numbers (one per flow), each rounded to discrete 0–4.  
**Reward (C++):**

```
reward = 20 * (total_throughput_mbps / 10) + 20 * Jain_fairness - avg_delay_penalty - loss_penalty
```

**Why CTDE?**  
Centralised training with a single policy and shared reward, but evaluation can be done per agent independently. This is the standard MARL paradigm for cooperative tasks.

---

## Experiment 5: MARL Training

**Setup:**
- Program: `marl-multi-tcp` (separate folder so `startSim` auto‑launches it)
- Agents: 2
- PPO: default SB3 hyperparameters, 100,000 timesteps
- Training reward: plateaued around **19,700**

**Result:** The reward was positive from the start because the fairness and throughput terms gave large positive values. The policy remained stable.

---

## Experiment 6: MARL Evaluation

**Evaluation metrics (two RL flows):**

| Flow | Throughput | Delay | Loss |
|------|------------|-------|------|
| Agent 1 | 5112.1 kbps | 60.96 ms | 0.04% |
| Agent 2 | 4824.8 kbps | 60.80 ms | 0.05% |

**Jain Fairness Index:** 0.9992  
**Total throughput:** 9936.9 kbps (99.37% of bottleneck)

**Interpretation:**  
The shared policy learned to divide the bottleneck almost perfectly fairly while keeping total utilisation near 100%. Delay is comparable to CUBIC, and loss is negligible.

---

## Bugs Found and Fixed

| Bug | Location | Impact | Fix |
|-----|----------|--------|-----|
| Fake throughput observation | `marl-rl-env.cc` `GetObservation()` | Agent couldn't see real throughput | Use PacketSink RX bytes |
| Action set absolute cwnd | `marl-rl-env.cc` `ExecuteActions()` | cwnd never grew | Store multiplier, apply in `IncreaseWindow()` |
| Missing `GetTcpState` getter | `tcp-socket-base.h` | Could not access TCP state in multi‑agent env | Added public getter |
| OpenGymInterface lacked `SetGymEnv` | `marl-multi-sim.cc` | Crash when starting | Used `SetOpenGymInterface` and `NotifyCurrentState` |
| Wrong program launched by ns3‑gym | Python subprocess format | Single‑agent program started instead of multi‑agent | Changed subprocess args to one string |
| Observation too large for PPO | No normalisation | NaN loss | Normalised observations in Python |

---

## Files Modified

- `tcp-socket-base.h` / `.cc` – added `GetTcpState()`
- `marl-multi-env.h` / `.cc` – custom multi‑agent gym environment
- `marl-multi-sim.cc` – dumbbell with two RL flows
- `marl_multi_env.py` – Python wrapper with normalisation
- `train_marl_multi.py` – one‑script training
- `eval_marl_multi.py` – evaluation and fairness
- `ppo_marl_multi.zip` – trained shared policy
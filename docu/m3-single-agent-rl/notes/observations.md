# M3 Observations: Single‑Agent RL Training and Evaluation

**Date:** 09 August 2026

**Author:** Okafor Kosisochukwu Johnpaul (Kss)

**Environment:** ns‑3 on Linux Mint Cinnamon, Python 3.12, venv, ns3‑gym

---

## 1. Experiment Setup

I deployed a Proximal Policy Optimization (PPO) agent to control a single TCP sender's congestion window (`cwnd`) with a 100 ms decision interval.

* **State Space (4 metrics):** `cwnd` (bytes), smoothed RTT (ms), loss rate (0 to 1), throughput (bytes/s).
* **Action Space (5 discrete multipliers):** $\times 1.0$, $\times 1.1$, $\times 0.9$, $\times 1.2$, $\times 0.8$ applied to `cwnd`.
* **Objective:** Optimize the throughput/delay/loss trade-off across three reward function variants (v1, v2, v3) on a dumbbell topology against an M2 CUBIC baseline.

---

## 2. Empirical Results

All three RL reward variants converged to the exact same conservative behavior, drastically underperforming CUBIC in throughput but overperforming in latency and loss.

| Metric | RL Agent (v1/v2/v3) | CUBIC (M2 Baseline) | Delta |
| --- | --- | --- | --- |
| **Throughput** | ~209 kbps | 2745 kbps | **-92.4%** |
| **Mean Delay** | ~22.8 ms (near 20 ms physical base) | 62.8 ms | **-63.7%** |
| **Packet Loss** | 0.00% | 0.19% | **-100%** |

### The Reward Illusion

The training curves showed artificial convergence, completely decoupled from real network performance:

* **v1 (Decaying-max):** Reward progressed from $-259$ to $-165$.
* **v2 (Direct throughput):** Reward progressed from $-5780$ to $-68$.
* **v3 (cwnd-target):** Reward progressed from $-262$ to $+2.87$ (positive final reward).

**Reality:** Throughput remained flat at 209 kbps across all three models.

---

## 3. Root Cause Analysis: The Broken Metric

The failure stems from a critical bug in the observation data, not the RL algorithm.

Inside `TcpTimeStepGymEnv`, the C++ code calculated throughput by summing instantaneous `bytesInFlight` snapshots and dividing by the step time. This yielded meaningless, near-zero values instead of true delivered throughput.

**The Mathematical Consequence:**
Because the state observation for throughput was essentially zero, the agent never received a positive signal for pushing data. The delay and loss penalties became the sole drivers of the policy. The PPO algorithm ruthlessly optimized for this by maintaining a microscopic `cwnd` to avoid any latency or drop penalties, creating a "safe but useless" policy.

Even in v3, where I rewarded `cwnd` directly against the Bandwidth-Delay Product (BDP) target, the mathematical penalty for missing the target was too weak to override the agent's fear of the delay penalty.

---

## 4. Engineering Takeaways

1. **Garbage In, Garbage Out:** If the agent cannot observe the true consequences of its actions, reward engineering is irrelevant. The metrics dictate the ceiling.
2. **Accidental QoS Discovery:** The RL agent successfully learned a zero-loss, ultra-low-latency policy. While terrible for bulk file transfers, this proves the agent *can* optimize for real-time application constraints (VoIP, gaming) when heavily penalized for queuing delay.
3. **Training Curves Lie:** Positive reward trends do not equal system-level success. End-to-end evaluation on actual network metrics is mandatory.
4. **Infrastructure Validated:** Despite the C++ metric flaw, the ns3-gym ZMQ bridge between Python and ns-3 handled hours of training without runtime crashes.

---

## 5. M4 Action Plan

1. **Patch the Pipeline:** Modify the C++ environment to extract true delivered throughput directly from the `PacketSink`.
2. **Force Contention:** Introduce a second CUBIC flow to the dumbbell topology to force the agent to fight for bandwidth.
3. **Execute MARL:** Retrain in this competitive, multi-agent setting with the corrected observation space.
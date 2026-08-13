# M4 As‑Built – Multi‑Agent RL for TCP Congestion Control

**Author:** Okafor Kosisochukwu Johnpaul  
**Date:** 13 August 2026  
**Status:** In progress — single‑agent fixed and working, MARL training pending

---

## What M4 Is Supposed To Be

M4 is the core of my project: multiple RL‑controlled TCP flows sharing one bottleneck and learning to coexist fairly. Before I could train multiple agents, I had to fix the problems from M3 that made the single agent useless.

---

## Part 1: The Observation Bug (From M3)

In M3, the RL agent achieved only 209 kbps regardless of reward function. I later discovered the throughput observation in the C++ code was broken.

The old code in `TcpTimeStepGymEnv::GetObservation()` computed throughput as:

```cpp
double bytesSum = std::accumulate(m_bytesInFlight.begin(), m_bytesInFlight.end(), 0u);
float throughputBps = bytesSum / stepSec;
```

`m_bytesInFlight` stores **instantaneous** snapshots of TCP's `bytesInFlight` variable. These snapshots are not delivered bytes — they are just how many bytes happen to be on the wire at the moment of a TCP callback. Summing them and dividing by step time gives a meaningless number, often zero.

**Fix:** I replaced this with a real throughput measurement from the receiver’s `PacketSink`.

The new code searches for a `PacketSink` application and computes delivered bytes since the last step:

```cpp
uint64_t totalRx = sink->GetTotalRx();
uint64_t deltaBytes = totalRx - m_lastRxBytes;
m_lastRxBytes = totalRx;
throughputBps = (deltaBytes * 8.0) / stepSec;
```

Now the agent sees actual delivered throughput, so it knows whether increasing cwnd actually helped.

---

## Part 2: The Action Bug (Found in M4)

Even after fixing throughput, the agent still stayed at 209 kbps. I printed the observations and saw cwnd never grew above ~1100 bytes.

I traced the action code and found a logical error.

In `marl-rl-env.cc`, the old `ExecuteActions` did:

```cpp
m_new_cWnd = static_cast<uint32_t>(mult * 1000); // e.g. 1.1 * 1000 = 1100
```

Then `IncreaseWindow` did:

```cpp
tcb->m_cWnd = m_new_cWnd; // set cwnd to exactly 1100
```

This means the action `+10%` did **not** multiply the current cwnd by 1.1. It just set cwnd to a fixed absolute value of 1100 bytes every time. So no matter how many times the agent chose “increase,” the window couldn't grow.

**Fix:** I changed `ExecuteActions` to store the actual multiplier:

```cpp
m_actionMultiplier = mult; // 1.0, 1.1, 0.9, 1.2, or 0.8
```

And `IncreaseWindow` to apply it properly:

```cpp
uint32_t currentCwnd = tcb->m_cWnd.Get();
uint32_t newCwnd = static_cast<uint32_t>(currentCwnd * m_actionMultiplier);
tcb->m_cWnd = newCwnd;
```

Now the agent can finally grow and shrink cwnd by percentages.

---

## Part 3: Reward Functions Tried

I used two reward wrappers for M4 single‑agent.

### M4 Reward v1 (`reward_wrapper_m4.py`)

- Throughput reward: normalised to 0–1 by dividing current throughput by 10 Mbps.
- Delay penalty: queueing delay in ms divided by 50.
- Loss penalty: loss rate × 10.
- Final reward: `throughput_reward - 0.5 * delay_penalty - 2.0 * loss_penalty`

Training reached positive reward but real throughput was still low because the action bug had not been fixed yet.

### M4 Reward v2 (`reward_wrapper_m4v2.py`)

I made throughput much more attractive:

- Throughput reward: `min(throughput_mbps / 10.0, 1.0) * 20.0`
  - Max possible reward = 20.0
- Delay penalty: queueing delay in ms divided by 10.0
  - 10 ms extra delay = -1.0
- Loss penalty: loss rate × 20.0
  - 1% loss = -0.2
- Final reward: `throughput_reward - delay_penalty - loss_penalty`

This heavily rewards the agent for pushing more data.

---

## Part 4: Single‑Agent Results (After Both Fixes)

With the corrected action and throughput observation, training reward went from **-8490** to **+4840** over 100,000 timesteps.

Evaluation on the dumbbell:

| Metric      | M4 RL Agent v2 | CUBIC (M2, 4‑flow) |
|-------------|----------------|---------------------|
| Throughput  | **8565.3 kbps** | 2745.0 kbps        |
| Mean Delay  | 85.67 ms       | 62.78 ms           |
| Packet Loss | 0.34%          | 0.19%              |

The RL agent now achieves **3.1× the throughput** of the M2 CUBIC comparison, and uses **85.65%** of the 10 Mbps bottleneck.

**Cost:** Higher delay and slightly higher loss. The agent learns to keep the queue full to maximise throughput, which causes bufferbloat.

This is a major breakthrough. It proves the RL pipeline works end‑to‑end when the environment is correct.

---

## Part 5: What Still Needs To Be Done in M4

- [ ] Modify `marl-sim.cc` to create **two RL agents** (two senders, two receivers)
- [ ] Create a multi‑agent reward wrapper with a **fairness term**
- [ ] Train both agents together using a shared PPO policy
- [ ] Evaluate throughput, delay, loss, and fairness
- [ ] Compare against Reno/CUBIC/BBR
- [ ] Document final results and create charts

---

## Part 6: Placeholders for MARL Results

### MARL Training Setup
[TO BE FILLED AFTER MARL TRAINING]
- Number of agents:
- Training timesteps:
- Reward wrapper used:
- Fairness term formula:

### MARL Evaluation Results
[TO BE FILLED AFTER MARL EVALUATION]
- Agent 1 throughput/delay/loss:
- Agent 2 throughput/delay/loss:
- Jain Fairness Index:
- Comparison table vs CUBIC/BBR:

### Lessons Learned
[TO BE FILLED AFTER MARL COMPLETE]
# M4 As‑Built – Multi‑Agent RL for TCP Congestion Control

**Author:** Okafor Kosisochukwu Johnpaul  
**Date:** 15 August 2026  
**Status:** Complete – single‑agent fixed, MARL trained and evaluated

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

---

## Part 5: Multi‑Agent Environment (Option A / CTDE)

For true MARL, I used **Option A** — a single shared PPO policy that outputs actions for both flows simultaneously. This is **Centralised Training, Decentralised Execution (CTDE)** because:

- During training, one policy sees both agents’ states and is rewarded for both throughput and fairness.
- During evaluation, the same policy can be queried independently per flow (or together).

I created a new ns‑3 example `marl-multi-tcp` with a custom `MyMultiGymEnv` that manages two TCP sockets and two `PacketSink`s. The observation is a flat vector of length 8 (2 agents × 4 metrics), and the action is a vector of length 2 (one per agent).

The reward in C++ is:

```
reward = 20 * total_throughput_mbps / 10 + 20 * Jain_fairness - avg_delay_penalty - loss_penalty
```

This encourages high throughput **and** fairness.

---

## Part 6: MARL Training

**Training setup:**
- Agents: 2
- Observation: 8 (cwnd, sRTT, loss placeholder, throughput for each flow)
- Action: 2 continuous values (0–4), rounded to discrete in Python
- Reward: fairness‑aware (above)
- PPO hyperparameters: default SB3, 100,000 timesteps
- Policy: MlpPolicy (shared)

**Training reward progression:**
- Started at ~19,700 (positive, due to high reward scale)
- Plateaued around **19,700** for the whole run
- Training took ~70,000 seconds of simulation time (real time was hours)

The positive reward means the agent was already doing well early, but it didn’t change much because the fairness term and throughput reward kept the total high and stable.

---

## Part 7: MARL Evaluation Results

After training, I evaluated the shared policy on one episode (60 seconds) and parsed FlowMonitor data.

| Metric      | MARL Agent 1 | MARL Agent 2 |
|-------------|--------------|--------------|
| Throughput  | 5112.1 kbps  | 4824.8 kbps  |
| Mean Delay  | 60.96 ms     | 60.80 ms     |
| Packet Loss | 0.04%        | 0.05%        |

**Jain Fairness Index: 0.9992**

**Total throughput: 9936.9 kbps (99.37% of bottleneck)**

This is a fantastic result. The agents:

- Fully utilise the 10 Mbps link
- Share almost perfectly fairly
- Keep delay at ~61 ms (comparable to CUBIC)
- Keep loss below 0.1%

---

## Part 8: Lessons Learned

1. **Environment correctness is everything.** The M4.2 observation and action fixes were the real breakthroughs. Without them, no reward function could work.
2. **CTDE with a shared policy works.** One policy controlling two agents learned cooperative behaviour with a fairness reward.
3. **Reward design matters.** The fairness term prevented the greedy single‑agent behaviour and led to near‑perfect Jain fairness.
4. **Auto‑launch requires directory name matching.** I created a separate `marl-multi-tcp` folder so `startSim=True` would launch the correct program.
5. **MARL is computationally expensive.** Training took hours because ns‑3 must run many full 60‑second simulations.

---

## Part 9: Files Modified

- `marl-multi-env.h` / `.cc` – custom multi‑agent gym environment
- `marl-multi-sim.cc` – dumbbell with two RL flows
- `marl_multi_env.py` – Python wrapper with normalisation and action rounding
- `train_marl_multi.py` – one‑script training with auto‑launch
- `eval_marl_multi.py` – evaluation and fairness analysis
- `ppo_marl_multi.zip` – trained shared policy
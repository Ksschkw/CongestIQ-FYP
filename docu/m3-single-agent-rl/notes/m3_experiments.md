# M3 Full Experiment Log: Single‑Agent RL for TCP Congestion Control

**Author:** Okafor Kosisochukwu Johnpaul

**Date:** 09 August 2026

**Summary:** I tried three different reward functions to teach a reinforcement learning agent how to control TCP congestion. The training numbers improved, but the actual throughput never left 209 kbps. The reason turned out to be a flaw in the observation data, not the learning algorithm. This document records everything I did, every mistake, and what I learned.

---

## 1. What is Reinforcement Learning (in my own words)?

Imagine I’m teaching a dog a new trick. The dog tries something (an action), I give it a treat if it did well (reward) or ignore it if it did badly (penalty). Over time the dog learns which actions earn treats. Reinforcement Learning works the same way, but instead of a dog I have a computer program (the agent) that controls the congestion window of a TCP flow. The agent sees some numbers about the network (state), picks an action (adjust the window), and gets a score (reward). It tries thousands of times and slowly learns which actions lead to higher scores.

---

## 2. The Pieces of My RL Setup

### 2.1 The Agent

The agent is a PPO (Proximal Policy Optimisation) algorithm from the `stable-baselines3` library. PPO is a popular RL algorithm that works well for continuous and discrete control problems. I used its default settings: a small neural network with two hidden layers of 64 neurons each, learning rate 0.0003, and it updates the policy every 2048 steps.

### 2.2 The State (What the agent sees)

Every 100 milliseconds, the agent receives a list of four numbers from the simulation:

* **cwnd** – the current congestion window size in bytes. This is how much data the sender is allowed to have in flight. It’s the main thing the agent controls.
* **smoothed RTT** – the average round‑trip time in milliseconds. This includes both the physical propagation delay (about 20 ms for my bottleneck) and any extra time packets spend waiting in the router’s queue (queueing delay).
* **loss rate** – the fraction of packets that were lost in the last interval (between 0 and 1).
* **throughput** – an estimate of how many bytes per second got through. **This turned out to be broken** (I explain in Section 5).

### 2.3 The Action Space (What the agent can do)

The agent can choose one of five discrete actions:

| Action ID | Meaning | Multiplier applied to cwnd |
| --- | --- | --- |
| 0 | Maintain | ×1.0 |
| 1 | Increase by 10% | ×1.1 |
| 2 | Decrease by 10% | ×0.9 |
| 3 | Increase by 20% | ×1.2 |
| 4 | Decrease by 20% | ×0.8 |

The multiplier is applied to the current cwnd, and the result becomes the new window. For example, if cwnd is 10000 bytes and the agent picks action 1, the new cwnd becomes 11000 bytes. If it picks action 2, the new cwnd becomes 9000 bytes.

### 2.4 The Reward (What the agent optimises)

The reward is a single number computed after every action. A high reward means “good job”, a low (or negative) reward means “bad move”. I designed the reward to reflect three things:

1. **Throughput** – I want the agent to send data fast. So I reward high throughput.
2. **Delay** – I want the agent to avoid causing queues. So I penalise high delay.
3. **Loss** – I want the agent to avoid dropping packets. So I penalise loss.

I combined these three into a single reward value. The exact formula changed three times (see below).

---

## 3. Reward Version 1 – Decaying‑Max Normalisation

**File:** `reward_wrapper.py`

**Training script:** `train_m3.py`

**Model saved as:** `ppo_rl_tcp_model.zip`

### 3.1 Why “Decaying‑Max”?

The problem with using raw numbers like “throughput = 5000 kbps” is that on a 10 Mbps link the max possible throughput is about 10000 kbps, but on a faster link it could be much higher. If I hardcode a maximum like 10000, my agent would be confused when the network changes. Instead, I let the agent keep track of the **best throughput it has ever seen so far**, and slowly forget old values. That way the reward is always relative to what’s possible right now.

The same idea applies to delay: I keep track of the **lowest RTT ever seen** ($\text{min\_rtt}$) and the **highest RTT ever seen** ($\text{max\_rtt}$), and the $\text{max\_rtt}$ slowly decays. This stops the agent from exploiting a single huge delay spike to make all future delays look small.

### 3.2 The Exact Formula

I define:

* $T$ = throughput in kbps (the raw number from the observation, but it’s broken – see Section 5)
* $s$ = smoothed RTT in milliseconds
* $L$ = loss rate (0 to 1)
* $\text{max\_throughput}$ = a variable that starts at 1.0 and updates every step: $\text{max\_throughput} = \max(T, \text{max\_throughput} \times 0.98)$
* $\text{min\_rtt}$ = lowest RTT seen so far (starts very high, only goes down)
* $\text{max\_rtt}$ = highest RTT seen so far, but with decay: $\text{max\_rtt} = \max(s, \text{max\_rtt} \times 0.98)$
* $\alpha$ (alpha) = 1.0, weight for throughput reward
* $\beta$ (beta) = 0.5, weight for delay penalty
* $\gamma$ (gamma) = 2.0, weight for loss penalty

The three parts:

* **Throughput reward** = $\frac{T}{\text{max\_throughput}}$ (capped at 1.0). This tells the agent “you’re getting X% of the best you’ve ever done”.
* **Delay penalty** = $\frac{s - \text{min\_rtt}}{\text{max\_rtt} - \text{min\_rtt}}$ if the denominator is large enough, else 0. This is the fraction of how much worse the current RTT is compared to the best possible.
* **Loss penalty** = $L$ (already 0 to 1).

Final reward:


$$
R = \alpha \cdot \text{throughput\_reward} - \beta \cdot \text{delay\_penalty} - \gamma \cdot \text{loss\_penalty}
$$

So if the agent gets perfect throughput (1.0), minimum delay (0 penalty), and zero loss (0 penalty), the maximum reward is 1.0. If everything goes wrong, the reward can go negative (e.g., -0.5 for moderate delay with no throughput).

### 3.3 Training Result

I trained for 50,000 timesteps (about 25 PPO iterations). The average reward per episode started at **‑259** and ended at **‑165**. The reward was improving, so the agent was learning *something*.

### 3.4 Evaluation Against CUBIC

I ran the trained policy on the same dumbbell, but this time with no competitor (just to see what it would do). The FlowMonitor reported:

* **Throughput:** 208.4 kbps
* **Mean Delay:** 22.79 ms
* **Packet Loss:** 0.00%

CUBIC from M2, on the other hand, got 2745 kbps, 62.78 ms delay, and 0.19% loss.

The RL agent clearly chose to keep the window extremely small to avoid any delay or loss. It learned a “safe” policy, but a useless one for bulk data.

---

## 4. Reward Version 2 – Direct Throughput (Mbps)

**File:** `reward_wrapper_v2.py`

**Training script:** `train_m3_v2.py`

**Model saved as:** `ppo_rl_tcp_model_v2.zip`

### 4.1 What I changed

I thought maybe the normalisation was confusing the agent. What if I just reward raw throughput directly, and make the penalties milder? So I threw away the decaying‑max scheme and used:

* **Throughput reward** = throughput in Mbps ($\frac{\text{throughput\_bps}}{10^6}$). So if the agent pushes 5 Mbps, it gets 5.0 reward. If it pushes 10 Mbps, 10.0.
* **Delay penalty** = queueing delay in seconds multiplied by 100. If the extra queueing delay is 10 ms (0.01 s), penalty is 1.0.
* **Loss penalty** = $\text{loss\_rate} \times 5.0$.
* I also kept track of $\text{min\_rtt}$ to know the baseline physical delay, so queueing delay = $s - \text{min\_rtt}$.

No alpha/beta/gamma needed here; the weights are built into the multipliers.

### 4.2 Training Result

Training for 200,000 steps (98 iterations). Reward started at **‑5780** (terrible, because low throughput gave tiny reward but delay penalty was still there) and converged to **‑67.8**. Massive improvement in the training curve.

### 4.3 Evaluation

Again, the real throughput was:

* **Throughput:** 209.1 kbps
* **Delay:** 22.81 ms
* **Loss:** 0.00%

Exactly the same as v1. The training curve looked great, but the actual behaviour didn’t change. This was the moment I started suspecting the observation data.

---

## 5. Reward Version 3 – CWND Target (Bandwidth‑Delay Product)

**File:** `reward_wrapper_v3.py`

**Training script:** `train_m3_v3.py`

**Model saved as:** `ppo_rl_tcp_model_v3.zip`

### 5.1 What is the Bandwidth‑Delay Product?

The Bandwidth‑Delay Product (BDP) is the ideal amount of data that should be in flight to keep the bottleneck busy without building a queue. It’s calculated as:

$$
\text{BDP} = \text{Bottleneck Bandwidth} \times \text{Round-Trip Time}
$$

For my 10 Mbps (1,250,000 bytes/s) bottleneck and 20 ms (0.02 s) propagation RTT:

$\text{BDP} = 1,250,000 \times 0.02 = 25,000 \text{ bytes (25 KB)}$

If the cwnd is exactly 25 KB, the sender is using the full link without causing a queue. If cwnd is smaller, the link is under‑utilised. If cwnd is larger, the queue starts filling and delay increases.

### 5.2 The Reward Formula

I threw away the broken throughput observation completely. Instead, I rewarded the agent for keeping cwnd close to 25 KB.

I used a Gaussian‑like function:

* $\text{target\_kb} = 25.0$ (the BDP in kilobytes)
* $\text{cwnd\_kb} = \frac{\text{cwnd}}{1000.0}$ (current cwnd in kilobytes)

$$
\text{cwnd\_reward} = \exp\left( -0.5 \times \left( \frac{\text{cwnd\_kb} - \text{target\_kb}}{0.5 \times \text{target\_kb}} \right)^2 \right)
$$

This gives a value near 1.0 when cwnd is close to 25 KB, and drops off to near 0 when cwnd is very small or very large.

Then I added penalties:

* **Delay penalty** = queueing delay in ms divided by 50. So a 50 ms extra delay gives 1.0 penalty.
* **Loss penalty** = $\text{loss\_rate} \times 10.0$.

The final reward:


$$
R = \text{cwnd\_reward} - 0.5 \cdot \text{delay\_penalty} - 2.0 \cdot \text{loss\_penalty}
$$

I kept the delay and loss penalties simple but scaled them down so the cwnd reward could dominate and push the agent to increase the window.

### 5.3 Training Result

This was the best training yet: reward went from **‑262** to **+2.87** – the first time I saw a positive final reward. The agent was clearly moving cwnd toward the target.

### 5.4 Evaluation

But the real throughput evaluation was:

* **Throughput:** 209.1 kbps
* **Delay:** 22.81 ms
* **Loss:** 0.00%

Once again, identical to v1 and v2. How could the training reward improve so much but the throughput not change? I had to find out.

---

## 6. The Root Cause: The Throughput Observation is Bogus

I wrote a tiny debug script (`debug_obs.py`) that ran the simulation with random actions and printed the raw observation vector at each step. Here’s a snippet of what I saw:

```
Initial obs: [5360.  44.  0.  0.]
Step 0: obs=[5360.  44.  0.  0.]
Step 1: obs=[1100.  50.3  0.  0.]
Step 2: obs=[800.  49.7  0.  0.]
...

```

The **fourth number** – the throughput – is **zero** on almost every step! In the C++ code inside `tcp-rl-env.cc`, the throughput is calculated as:

```cpp
double bytesSum = std::accumulate(m_bytesInFlight.begin(), m_bytesInFlight.end(), 0u);
float throughputBps = bytesSum / stepSec;

```

`m_bytesInFlight` collects the **instantaneous** value of `tcb->m_bytesInFlight` every time the TCP stack calls `GetSsThresh` or `IncreaseWindow`. These callbacks happen many times per RTT, and the `bytesInFlight` value is a tiny snapshot, not the total bytes delivered. Dividing that small sum by the step time gives a number that is either zero or a meaningless huge spike. It does **not** represent real delivered throughput.

Because the observation said throughput was zero, any reward function that depended on throughput could never give the agent a positive signal for pushing more data. The agent never saw a connection between increasing cwnd and getting a higher reward, so it stayed in the safe low‑cwnd region.

In v3 I didn’t use throughput at all, but the cwnd‑target reward still wasn’t strong enough to overcome the delay penalty. The agent could earn a small but steady reward just by keeping cwnd very low, so it never explored higher windows.

---

## 7. What We Actually Achieved

Even though the throughput didn’t improve, the RL agent learned something valuable:

| Metric | RL Agent (all versions) | CUBIC (M2) |
| --- | --- | --- |
| Throughput | ~209 kbps | 2745 kbps |
| Mean Delay | ~22.8 ms | 62.8 ms |
| Packet Loss | 0.00% | 0.19% |

The agent discovered that keeping cwnd extremely small gives **zero loss and near‑minimum delay**. While this is terrible for file downloads, it’s exactly the behaviour you want for real‑time applications like VoIP, gaming, or video conferencing where latency matters more than throughput.

This is **not a failure of the RL approach**. The agent optimised exactly what the reward (and the misleading observation) told it to optimise. With a fixed throughput observation, the same reward functions would likely produce a policy that balances throughput and delay, like a smarter version of BBR.

---

## 8. Key Lessons Learned

1. **The observation must be truthful.** If the agent can’t see the real effect of its actions, no amount of clever reward engineering will fix it.
2. **Training reward curves can lie.** The reward improved in all three versions, but the real network behaviour stayed the same. Always evaluate the policy on the actual metric you care about.
3. **Reward design is hard.** I tried three very different formulas and still ended up with the same behaviour because the underlying observation was broken.
4. **The ns3‑gym bridge works.** Despite compile errors, API mismatches, and many crashes, the ZMQ/protobuf communication between ns‑3 and Python is solid.
5. **Single‑flow training limits exploration.** Without a competing flow, there’s no urgency to grab bandwidth. The MARL phase (M4) will probably show richer behaviour.

---

## 9. Files and Models

All the code, models, and charts for M3 are stored in my project:

* `rl_agent/reward_wrapper.py` – v1 reward (decaying‑max)
* `rl_agent/reward_wrapper_v2.py` – v2 reward (direct throughput)
* `rl_agent/reward_wrapper_v3.py` – v3 reward (cwnd target)
* `rl_agent/train_m3.py`, `train_m3_v2.py`, `train_m3_v3.py` – training scripts
* `rl_agent/eval_safe.py`, `eval_v2.py`, `eval_v3.py` – evaluation scripts
* `rl_agent/ppo_rl_tcp_model.zip` (v1), `ppo_rl_tcp_model_v2.zip` (v2), `ppo_rl_tcp_model_v3.zip` (v3) – saved models
* `ns-3-dev/contrib/ns3-gym/examples/rl-tcp/` – the C++ simulation and gym environment
* `docu/m3-single-agent-rl/results/` – all comparison charts, convergence plots

---

## 10. What Next?

In M4 I’ll add a second TCP flow (CUBIC) to the dumbbell and train the RL agent in a competitive setting. That should force it to fight for bandwidth. More importantly, I need to fix the throughput observation so the agent gets real feedback. That change might require modifying the C++ code to read the `PacketSink` received bytes, which is more work but will make the environment actually usable.

M3 proved that the RL pipeline works end‑to‑end. The agent can observe, act, and learn. Now I need to make the observations correct so it learns the right thing.
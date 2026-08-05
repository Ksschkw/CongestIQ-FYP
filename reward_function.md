## The Reward Function (Single‑Agent, M3)

$$R_t = \alpha \cdot \text{throughput\_reward} - \beta \cdot \text{delay\_penalty} - \gamma \cdot \text{loss\_penalty}$$

This is the **scalar number** the agent receives after each decision interval (once per RTT). It wants to **maximise the sum over time**.

I’ll now break each term into:

* What it represents in the network
* Exactly how I compute it from TCP/socket variables
* How I normalise it so all terms live on a similar scale

---

### 1. Throughput Reward ($\text{throughput\_reward}$)

**What it means:**

The agent should get a high reward when it successfully delivers data quickly. It must not just send blindly – the delivery rate matters.

**How to measure it:**

Between two decision steps (time $t$ and $t+1$), the receiver’s `PacketSink` has received some bytes. The throughput during that interval is:

$$\text{throughput} = \frac{\text{bytes\_received\_since\_last\_step} \times 8}{\text{interval\_duration}}$$

The interval duration is roughly one RTT (I can use the smoothed RTT value at the start of the step).

I then normalise this by the **bottleneck capacity** (10 Mbps = 10,000 kbps). So:

$$\text{throughput\_reward} = \frac{\text{throughput (kbps)}}{10\,000}$$

This yields a number in roughly [0, 1] (since I can’t exceed the bottleneck). I can cap it at 1.0.

**Why normalise?** Keeps the scale comparable with the other terms.

**Where to get the data in ns‑3:**

The C++ gym environment can attach a trace to the `PacketSink` application or simply read the sink’s `GetTotalRx()` at every step and compute the delta.

---

### 2. Delay Penalty ($\text{delay\_penalty}$)

**What it means:**

The agent should be punished when packets spend a lot of time waiting in queues. High delay = congestion building up, even if no packets have been dropped yet.

**How to measure it:**

The TCP socket gives I the smoothed RTT (`srtt`), which is the average round‑trip time including queueing. The **minimum possible RTT** on My network is the physical propagation delay of the path: 2×20 ms (bottleneck round‑trip) + 2×1 ms (access) = 42 ms.

So the “queueing delay” is:

$$\text{queueing\_delay} = \max(0, \text{srtt} - \text{min\_rtt})$$

Then I normalise by a maximum acceptable queueing delay, say 100 ms:

$$\text{delay\_penalty} = \frac{\text{queueing\_delay}}{100}$$

This is 0 when srtt is at minimum, and approaches 1 when srtt reaches 142 ms.

**Why not just use srtt directly?** Because I want the agent to differentiate between propagation delay (unavoidable) and queue buildup (which it can control).

**Where to get the data:**

`ns3::TcpSocketBase::GetRttEstimate()` gives me the current RTT estimate in seconds.

---

### 3. Loss Penalty ($\text{loss\_penalty}$)

**What it means:**

Dropped packets are a direct sign that the agent pushed too hard. The agent must learn to avoid them.

**How to measure it:**

During the interval, count the number of packets sent ($\text{tx\_packets}$) and the number lost ($\text{lost\_packets}$). The loss rate is:

$$\text{loss\_rate} = \frac{\text{lost\_packets}}{\text{tx\_packets}}$$

That’s already in [0, 1]. I can use it directly:

$$\text{loss\_penalty} = \text{loss\_rate}$$

If no packets are sent (rare), set loss_penalty to 0.

**Where to get the data:**

TCP socket provides `GetLost()` for lost segments and `GetTxBuffer()` for total sent. Or I can accumulate the difference in the `PacketSink` received vs. sender’s sent bytes.

---

### 4. The Weights ($\alpha, \beta, \gamma$)

These control the **trade‑off** the agent learns. They are hyperparameters I can tune later, but start with values that make all terms equally important:

* $\alpha = 1.0$
* $\beta = 0.5$
* $\gamma = 10.0$

Why $\gamma$ so high? Because packet loss is the strongest signal of congestion – the agent should be really discouraged from causing any loss. Even a 1% loss rate would give a penalty of 0.1, which outweighs a throughput gain of 0.1.

I can experiment later, but this set gives a sensible starting point.

---

### 5. What the Agent Sees vs. What It’s Rewarded For

* **State** (observation) is what the agent sees *before* deciding. It includes cwnd, sRTT, delivery rate, etc.
* **Reward** is computed *after* the action has been applied and the network has evolved for one RTT. It tells the agent how Ill its last action worked.

The reward function uses metrics that capture the **consequences** of the action: did I get more throughput? Did I increase delay? Did I cause losses?

---

### 6. Why This Reward Function Works for My Project

* It directly encourages **high goodput**, not blind sending.
* It penalises **latency** before loss occurs, so the agent can learn to keep queues short.
* It harshly penalises **loss**, aligning with TCP’s original goal of avoiding congestion collapse.
* It’s **computable in real time** from ns‑3 socket statistics.

In M4 (MARL), I’ll add a **fairness term** that rewards agents when the bandwidth is shared equally. But for M3 with one RL flow, this three‑term reward is complete.
# M2 Observations: Multi-Flow Congestion Dynamics

**Date:** 20 June 2026  
**Author:** Okafor Kosisochukwu Johnpaul  
**Environment:** ns-3 on Linux, Python 3.12, venv

---

## What I Did

I expanded my M1 dumbbell topology to four TCP senders instead of two:

- **Flow 1 (Sender 0): TCP Reno**
- **Flow 2 (Sender 1): TCP CUBIC**
- **Flow 3 (Sender 2): TCP BBR**
- **Flow 4 (Sender 3): TCP CUBIC** (a second CUBIC flow)

All four flows share the same 10 Mbps bottleneck link with a 20 ms delay and a DropTail queue of 100 packets. The simulation ran for 60 seconds. I also added a new trace that records the exact number of packets waiting in the bottleneck queue every time it changes.

I generated per‑flow throughput, delay, and loss bar charts, a fairness score, and a time‑series graph of the queue occupancy.

---

## What I Saw

### Throughput
- Reno: **2277.6 kbps**
- CUBIC (Flow 2): **2745.0 kbps**
- BBR: **2045.4 kbps**
- CUBIC (Flow 4): **2878.0 kbps**

The total throughput adds up to about **9.95 Mbps**, which is almost exactly the bottleneck capacity (10 Mbps). The link is completely full. CUBIC flows grabbed the largest share, while BBR got the smallest.

### Delay
- Reno: **59.62 ms**
- CUBIC (Flow 2): **62.78 ms**
- BBR: **82.03 ms**
- CUBIC (Flow 4): **60.81 ms**

Three of the flows sit around 60 ms. BBR’s delay is much higher at 82 ms. The base propagation delay of my bottleneck is 20 ms, so the extra 40–60 ms is all queueing delay — packets waiting in the router’s buffer.

### Packet Loss
- Reno: **0.08%**
- CUBIC (Flow 2): **0.19%**
- BBR: **2.52%**
- CUBIC (Flow 4): **0.20%**

BBR’s loss rate is over ten times higher than the other flows. The loss‑based algorithms (Reno, CUBIC) keep their loss low by backing off when the queue overflows. BBR doesn’t back off from loss; it keeps probing, so its extra packets get dropped.

### Fairness
- **Jain’s Fairness Index: 0.9818** (scale 0 to 1, 1 = perfectly equal)

Even though CUBIC got about 30% more throughput than BBR, the fairness score is still very high. That’s because no single flow is starving completely — all four are within the range of ~2.0 to ~2.9 Mbps. The index sees that as "almost fair."

### Queue Occupancy (Bottleneck Queue Over Time)
The queue graph looks like a repeating jagged sawtooth. The number of packets in the queue shoots up to 100, stays there for a short time, then crashes down to a low value, and the cycle repeats.

This is the classic TCP AIMD (Additive Increase, Multiplicative Decrease) sawtooth. The senders slowly increase their sending rate (additive increase), which fills the queue. Once the queue hits 100 packets, a packet is dropped. The sender that detects the loss cuts its sending rate in half (multiplicative decrease), the queue drains rapidly, and the whole process starts over.

My queue is set to 100 packets, but the bandwidth‑delay product of this bottleneck is only about 18 packets — meaning the link only needs about 18 packets "in flight" to stay full. The extra queue space just adds delay without improving throughput. That’s bufferbloat.

---

## My Understanding

1. **BBR struggles in a mixed environment.** BBR is designed to keep queues small and latency low, but when it shares a bottleneck with aggressive CUBIC flows, the queue is almost always full. BBR’s periodic probes hit that full queue and suffer both high loss and high delay.

2. **CUBIC is the most aggressive algorithm here.** Its cubic window growth allows it to recover faster after loss and grab more bandwidth than both Reno and BBR. Both CUBIC flows got the highest throughput.

3. **Fairness is not the same as good performance.** The Jain index says 0.98 — very fair. But that "fairness" comes with an average delay of 60–80 ms and a queue that’s constantly hitting its limit. A truly smart congestion controller would achieve high fairness *without* that delay penalty.

4. **The sawtooth queue graph shows the problem I need to solve.** If I can train a MARL agent to smooth out those spikes — keeping the queue at maybe 20–30 packets instead of constantly slamming into 100 — I could keep throughput high while drastically reducing delay and loss. That’s exactly the goal for M3 and M4.

---

## Next Steps (M3)

I will set up the ns3‑gym bridge, build a custom OpenAI‑style environment, and train a single RL agent against a fixed TCP flow. Then I’ll move to multi‑agent training.
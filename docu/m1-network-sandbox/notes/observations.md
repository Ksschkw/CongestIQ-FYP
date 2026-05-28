# M1 Observations: Reno vs CUBIC on a Bottleneck

**Date:** 26 May 2026
**Author:** Okafor Kosisochukwu Johnpaul
**Environment:** ns-3 on Linux Mint Cinnamon, Python 3.12, venv

---

## What I Did

I built a dumbbell topology in ns-3 with two TCP senders:

- Sender 0 running **TCP Reno**
- Sender 1 running **TCP CUBIC**

Both senders tried to send as much data as possible for 60 seconds through a shared bottleneck link of 10 Mbps with 20 ms delay. I collected performance statistics using FlowMonitor and made graphs with a Python script.

---

## What I Saw

### Throughput

- **Reno (Flow 1):** 4611.3 kbps
- **CUBIC (Flow 2):** 5330.1 kbps

CUBIC achieved higher throughput. It took more of the available bandwidth than Reno.

### Delay

- **Reno:** 61.80 ms average delay
- **CUBIC:** 60.94 ms average delay

The delays were almost the same. The base propagation delay is 20 ms (bottleneck link), so the extra ~41 ms is queueing delay – the time packets spent waiting in the router's buffer.

### Packet Loss

- **Reno:** 0.02% loss (12 out of 58,878 packets sent)
- **CUBIC:** 0.04% loss (30 out of 68,091 packets sent)

Both flows experienced very little packet loss. CUBIC lost more packets in absolute numbers, but the loss rate was still tiny.

---

## My Understanding

1. **CUBIC is more aggressive than Reno.**After a packet loss, Reno grows its congestion window linearly (additive increase). CUBIC uses a cubic function that grows the window faster, especially when it is far from the last loss point. That lets CUBIC grab more bandwidth over time.
2. **The bottleneck queue caused delay, not loss.**I set the queue to 100 packets (DropTail). The simulation showed delays of ~61 ms, meaning packets spent a lot of time waiting in the queue. But very few packets were actually dropped (only 12 and 30 out of tens of thousands). The queue was full most of the time, but both algorithms are designed to back off before causing massive drops in this setup.
3. **Fairness was not perfect.**In a perfectly fair world, both flows would get 5 Mbps each (half of the 10 Mbps bottleneck). Here, CUBIC got more than half (~5.3 Mbps), and Reno got less (~4.6 Mbps). This is consistent with what I read about CUBIC being less fair to loss-based flows like Reno.
4. **NetAnim showed congestion visually.**
   In the animation, I could see many packets moving through the middle link between the two routers. The arrows were dense on that link, which represents the bottleneck. That matches the high queueing delay I saw in the numbers.

---

## What I Learned

- TCP congestion control algorithms do not share bandwidth equally. The choice of algorithm matters.
- Even with a small queue, greedy flows can build up delay without massive packet loss.
- FlowMonitor gives me everything I need: throughput, delay, loss – all in one XML file.
- I can now run a simulation, get numbers, and plot them. This is the foundation I'll use when I later compare my own RL agent against these baselines.

---

## Next Steps (M2)

I will run more flows (4+), add BBR, and look deeper into queue dynamics, fairness, and RTT patterns. Then I will start building the RL environment.

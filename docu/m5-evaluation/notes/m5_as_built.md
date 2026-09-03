# M5 As‑Built – Full Evaluation

**Author:** Okafor Kosisochukwu Johnpaul  
**Date:** 03 September 2026  
**Status:** Complete – baselines run, MARL comparison attempted with caveats

---

## Purpose

M5 evaluated the trained RL policy against traditional TCP variants (Reno, CUBIC, BBR) on a two‑flow dumbbell. Metrics: throughput, delay, loss, Jain fairness.

---

## Baseline Setup

- Topology: dumbbell, 2 senders, 2 receivers, 10 Mbps bottleneck, 20 ms delay, DropTail queue 100 packets
- Duration: 60 s
- FlowMonitor collected per‑flow stats

Runs:

```bash
./ns3 run "scratch/two-flow-baseline --tcp=TcpNewReno --duration=60"
./ns3 run "scratch/two-flow-baseline --tcp=TcpCubic --duration=60"
./ns3 run "scratch/two-flow-baseline --tcp=TcpBbr --duration=60"
```

---

## Baseline Results

| Variant | Flow 1 Throughput | Flow 2 Throughput | Avg Delay | Avg Loss | Jain Fairness |
|---------|-------------------|-------------------|-----------|----------|---------------|
| Reno    | 4968.7 kbps       | 4968.5 kbps       | 54.28 ms  | 0.016%   | 1.0000        |
| CUBIC   | 5112.1 kbps       | 4824.8 kbps       | 60.91 ms  | 0.047%   | 0.9992        |
| BBR     | 5142.7 kbps       | 4460.9 kbps       | 66.55 ms  | 0.394%   | 0.9950        |

---

## MARL Comparison (with caveat)

The MARL evaluation produced identical numbers to CUBIC, indicating the RL policy did not truly control cwnd. This is documented as a limitation in M4.

For completeness, the invalid MARL numbers were:

| Agent | Throughput | Delay | Loss |
|-------|------------|-------|------|
| 1     | 5112.1 kbps| 60.96 ms | 0.04% |
| 2     | 4824.8 kbps| 60.80 ms | 0.05% |

---

## Single‑Agent RL (valid)

The single‑agent RL policy from M4 v2 achieved:

- Throughput: 8565.3 kbps
- Delay: 85.67 ms
- Loss: 0.34%

This is the strongest valid RL result in the project.

---

## Charts Produced

- `m5_throughput_comparison.png`
- `m5_fairness_comparison.png`
- `m5_delay_comparison.png`
- `m5_loss_comparison.png`

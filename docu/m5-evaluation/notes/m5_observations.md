> **Update (October 2026).** Two values in this note are no longer the current
> ones. The Jain index of 0.9992 belongs to TCP CUBIC, not to the learned policy,
> and the multi-agent figures come from the broken run. The learned policy was
> later evaluated correctly and achieved 8696.3 kbps, 22.80 ms, 0.000 percent
> loss and a Jain index of 1.0000. See `m5_corrected_evaluation.md`.

# M5 Observations

## Baseline Differences

- **Reno** is the fairest (Jain 1.0000) and has the lowest delay (54.3 ms) and loss (0.016%).
- **CUBIC** is slightly less fair but still excellent (0.9992), with moderate delay and loss.
- **BBR** has the highest total throughput but the worst fairness (0.9950), highest delay (66.6 ms), and highest loss (0.394%).

## RL Performance

- Single‑agent RL achieves 8565 kbps but with high delay (85.67 ms) and loss (0.34%).
- The MARL two-agent result was unreliable until October 2026 because it mimicked CUBIC. After the correctness repair the learned policy achieved 8696.3 kbps, 22.80 ms, 0.000 percent loss and a Jain index of 1.0000.

## Key Insight

Traditional algorithms are already very good on simple two‑flow dumbbells. RL may offer benefits in more complex or heterogeneous environments, but demonstrating that requires full isolation of RL control.
# M5 Observations

## Baseline Differences

- **Reno** is the fairest (Jain 1.0000) and has the lowest delay (54.3 ms) and loss (0.016%).
- **CUBIC** is slightly less fair but still excellent (0.9992), with moderate delay and loss.
- **BBR** has the highest total throughput but the worst fairness (0.9950), highest delay (66.6 ms), and highest loss (0.394%).

## RL Performance

- Single‑agent RL achieves 8565 kbps but with high delay (85.67 ms) and loss (0.34%).
- MARL two‑agent result is unreliable because it mimics CUBIC.

## Key Insight

Traditional algorithms are already very good on simple two‑flow dumbbells. RL may offer benefits in more complex or heterogeneous environments, but demonstrating that requires full isolation of RL control.
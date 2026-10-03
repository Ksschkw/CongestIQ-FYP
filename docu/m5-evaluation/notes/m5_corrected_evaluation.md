# M5 corrected evaluation

Author: Okafor Kosisochukwu Johnpaul
Date: 3 October 2026

## Purpose

This note reports the corrected M5 evaluation, in which the learned multi-agent
policy genuinely controls the congestion window. It replaces the invalid
multi-agent numbers in the submitted report, which were produced by the ns-3
default algorithm, TCP CUBIC.

## Environment

- Topology: one dumbbell. Two senders, two routers, two receivers.
- Bottleneck: 10 Mbps, 20 ms one-way delay, DropTail queue of 100 packets.
- Access links: 100 Mbps, 1 ms.
- Traffic: two BulkSend flows, one per sender, running for 60 seconds.
- Baselines: TCP NewReno, TCP CUBIC and TCP BBR, set per sender with the
  `SocketType` attribute after the internet stack is installed.
- Learned policy: the shared policy from `ppo_marl_multi_v2.zip`, evaluated with
  the most likely action at each step, for three seeds.
- Metrics: per-flow throughput, mean delay, loss ratio and Jain fairness from the
  ns-3 FlowMonitor XML. Jain's fairness index measures how equally the flows
  share the link; a value of 1 means an exactly equal share.

## Results

| Scenario | Total throughput (kbps) | Utilisation | Mean delay (ms) | Loss (%) | Jain fairness |
| --- | --- | --- | --- | --- | --- |
| Reno | 9937.2 | 99.37% | 54.30 | 0.016 | 1.0000 |
| CUBIC | 9936.9 | 99.37% | 60.88 | 0.047 | 0.9992 |
| BBR | 9603.6 | 96.04% | 66.55 | 0.394 | 0.9950 |
| Learned policy (mean of 3 seeds) | 8696.3 | 86.96% | 22.80 | 0.000 | 1.0000 |

The two flows receive an equal share: 4348.2 kbps each. The three seeds produced
identical values because the policy is deterministic and the topology is
symmetric.

## What the learned policy does

The policy observes the congestion window, the smoothed round trip time, a loss
placeholder and the delivered throughput for both flows. It holds the congestion
window at about 23 KB, which is close to the bandwidth-delay product of the
bottleneck. That is the volume of data needed to keep the link busy without
building a standing queue. It raises the window while the window is below that
level and holds it once it is above.

The measured effect is a link that is 87 percent used, with almost no queueing
delay and no packet loss.

## Comparison and interpretation

Against CUBIC, the learned policy gives up about 12 percent of throughput and
takes about 63 percent less delay, with no measured loss and a perfect fairness
index. The delay is close to the base propagation delay of the path, so the
router queue stays almost empty. This matches the goal set out in Chapter One of
the report: keep the link well used while reducing queueing delay, and share the
link fairly.

The policy does not beat CUBIC on raw throughput, and the write-up says so.

## How the policy was obtained

This part is recorded in full because the final pipeline uses two stages.

1. A reward that weights throughput, fairness, queueing delay and the
   congestion window was defined. The full formula is in
   `marl-multi-env.cc`.
2. A simple reference controller was written for data collection only. It raises
   the window by 20 percent while the window is below 25 KB and holds it
   otherwise.
3. Demonstrations were collected by running the environment with random actions
   for part of each episode, so that many window sizes were visited, and labelling
   every visited state with the action that the reference controller would take.
4. The shared policy network was trained by behaviour cloning on those
   demonstrations. Behaviour cloning is supervised learning: the network learns
   to reproduce the reference action for the observed state. It reached 99.9
   percent agreement on the demonstrations and learned the window threshold.
5. The cloned policy was then refined with PPO, the same reinforcement learning
   algorithm used throughout the project, at a low learning rate.

The imitation stage exists because PPO trained from random weights kept
converging to a policy that raised the window at every step and flooded the
router queue. That policy earned about 33 reward points per step. A constant
action experiment showed that the reference behaviour earns about 73 points per
step, so the good operating point exists, but the policy gradient did not find
it. Imitation gives the policy a starting point near that operating point, and
PPO then refines it. This is a standard way to use demonstrations in
reinforcement learning, and the final policy is still the same PPO policy, in
the same multi-agent setup, choosing the same five window actions.

## Evidence that the policy controls the window

`docu/m4-marl-training/notes/m4_control_verification.md` records the test. Two
results matter. First, the program reads the congestion control object from each
live socket at runtime and it reports `NoOpTcpCongestion`, so ns-3's own
algorithm is not attached. Second, running the same topology with a constant
"hold the window" action keeps the window at exactly 5,360 bytes for the whole
run. A native loss-based algorithm cannot do that, because it grows the window on
every acknowledgment and cuts it on loss. The window therefore follows the
actions.

## Reward values of the constant actions

Under the final reward, the mean reward per step for each constant action over 15
seconds was:

| Constant action | Mean reward per step |
| --- | --- |
| decrease 20 percent | -40.82 |
| decrease 10 percent | -36.84 |
| hold | 28.71 |
| increase 10 percent | 0.25 |
| increase 20 percent | -8439.19 |

The learned policy earns about 56 points per step, well above every constant
action. The window term in the reward is what makes the flooding action so
costly.

## Files

- `m5_corrected_summary.csv` and `m5_corrected_summary.json`: the table above.
- `m5_corrected_comparison.png`: four panel comparison.
- `marl_v2_seed<N>.flowmon`: FlowMonitor XML for each seed.
- `marl_v2_seed<N>_cwnd.csv`: congestion window per step for each seed.
- `marl_v2_cwnd_traces.png`: congestion window against time.
- `marl-multi-animation.xml`: a short NetAnim trace of the learned policy.
- `baseline_Reno.flowmon`, `baseline_CUBIC.flowmon`, `baseline_BBR.flowmon`.

## How to reproduce

```bash
cd /home/ksschkw/Projects/fyp
venv/bin/python rl_agent/m5_evaluate.py --marl --seeds 1 2 3 --duration 60
venv/bin/python rl_agent/m5_evaluate.py --plot-only --marl
venv/bin/python rl_agent/verify_control.py --duration 15
```

## Figures

The figures that go into the report and the slides are generated from the result
files by `docu/make_report_figures.py`. They live in
`docu/m5-evaluation/results/figures/`.

| File | Used as | Content |
| --- | --- | --- |
| `fig_architecture.png` | Figure 3.1 | The two-process testbed. The Python policy process and the ns-3 simulation process exchange the state, the action and the reward through ZeroMQ and Protocol Buffers. |
| `fig_reward_landscape.png` | Figure 4.6 | Mean reward per step for each constant window action, before and after the reward was calibrated. |
| `fig_comparison.png` | Figure 4.7 | Four-panel comparison of the learned policy against Reno, CUBIC and BBR. |
| `fig_cwnd_trace.png` | Figure 4.8 | Congestion window of both agents over a 60-second run, against the fair share of the bandwidth delay product. |
| `fig_tradeoff.png` | Figure 4.9 | Throughput and delay trade-off scatter. |
| `fig_slide_metrics.png` | Slide 8 | The same comparison in a wide, short layout for the slide. |

The figures replace the two terminal screenshots that showed the invalid run.
`docu/insert_report_figures.py` rebuilds the corrected report and puts the
figures in place, and `docu/insert_slide_figures.py` does the same for the
slides. Both scripts regenerate their output from the original files first, so
they can be run again without duplicating anything. The report structure is
preserved: no paragraph is added or removed by the text corrections, and the
figure insertion only replaces image bytes and adds two new figures with their
captions.

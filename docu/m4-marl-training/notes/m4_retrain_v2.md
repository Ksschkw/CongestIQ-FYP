# M4 retrain v2: how the final multi-agent policy was produced

Author: Okafor Kosisochukwu Johnpaul
Date: 3 October 2026

## Why I retrained

The model from the original multi-agent run, `ppo_marl_multi.zip`, was trained
while ns-3's TCP CUBIC was changing the congestion window underneath the policy.
It is not a policy for the corrected environment. I kept it for the record and
produced a new model.

## What the corrected environment does

1. The no-op congestion control is attached to the sender sockets after the
   internet stack is installed, and the program aborts if the attachment fails.
   The policy therefore owns the congestion window. See
   `m4_root_cause_correction.md`.
2. FlowMonitor is disabled during training through the `--flowmon` switch. It is
   only needed for evaluation.
3. The congestion window observation uses a saturating transform instead of a
   linear one, so that window sizes above 100 KB remain distinguishable. A linear
   scale clips them, and a policy that floods the queue then cannot see how far it
   has overshot.

## The action space

Each agent has five window actions: hold, increase by 10 percent, decrease by 10
percent, increase by 20 percent, and decrease by 20 percent. These are the
actions defined in the report.

The action space is a joint discrete space with 5^2 = 25 values for two agents.
Agent 0 is the least significant digit. An earlier version used a continuous box
with one value per agent, rounded to the five levels in Python. With a continuous
space the PPO policy kept its output mean near the lower bound of the space and
relied on exploration noise, so its deterministic action was not the window
increase that the reward favoured. A discrete space makes the deterministic
action a real choice: the most likely action.

## The reward

```
reward = 60 * min(total_throughput_mbps / 10, 1)
       + 20 * jain_fairness
       - 0.3 * average_queueing_delay_ms
       - 20 * average_loss_rate
       - 0.0005 * average_congestion_window_bytes
```

The congestion window in the observation and in the reward is the sender's limit
on the volume of unacknowledged data it may keep in flight. The average queueing
delay is the smoothed round trip time minus the lowest smoothed round trip time
seen so far. The loss input is a placeholder of zero; loss is measured after the
run from FlowMonitor and is about 0.05 percent in this topology, so the loss term
has no effect on learning.

The window term is the important addition. The delay charge alone was not enough
to pull the policy away from flooding. With a charge of 0.0005 points per byte, a
25 KB window costs about 12 points per step, a held 5 KB window costs about 3, and
a flooded 500 KB window costs 250.

## Reward versions that were tried and rejected

| Version | Throughput weight | Delay charge | Window charge | Outcome |
| --- | --- | --- | --- | --- |
| Report reward | 20 | 1.0 per ms | none | Constant-action test gave the highest reward to holding a small window. A trained policy held about 5 KB and used 2.1 Mbps. |
| v2a | 40 | 0.1 per ms | none | The action order was changed at the same time, and the untrained policy collapsed the window. Episode reward about -6,250. |
| v2b | 60 | 0.05 per ms | none | The policy learned to raise the window at every step. It reached 8.8 Mbps but with 142 ms delay and 1.3 percent loss. |
| v2c | 60 | 0.15 per ms | none | A fine-tune did not change the policy, because the categorical policy had stopped exploring. |
| v2d | 60 | 0.3 per ms | none | Same flooding policy. |
| final | 60 | 0.3 per ms | 0.0005 per byte | The flooding action became very costly. A behaviour-cloned policy holds the window near the bandwidth-delay product and earns about 56 points per step. |

## The imitation warm-start

PPO trained from random weights kept converging to the flooding policy. To give
the policy a better starting point I used a reference controller and behaviour
cloning.

- Reference controller: raise the window by 20 percent while it is below 25 KB,
  hold it otherwise. This is close to the bandwidth-delay product of the
  bottleneck.
- Demonstrations: about 1,200 state and action pairs. Each episode used random
  actions for part of its length so that the window swept from about 0.5 KB to
  about 41 KB, and every visited state was labelled with the reference action for
  that state.
- Behaviour cloning: supervised training of the policy head with cross entropy.
  The first attempt reached a degenerate constant output because it used the
  log probability returned by Stable Baselines3's `evaluate_actions`, which
  produced a near-zero gradient here. A direct forward pass through the policy
  network fixed it. The clone reached 99.9 percent agreement with the reference,
  including 100 percent agreement on the window-increase transitions.
- Refinement: PPO continued from the cloned policy at a low learning rate. Over
  3,000 steps the mean episode reward moved from 33,582 to 34,276, and the
  network metrics were unchanged, so the refinement preserved the learned
  behaviour. The delivered model is the refined model.

The demonstration data is saved as `bc_demonstrations.npz`. The cloning is
implemented in `rl_agent/bc_warmstart.py`.

## Training configuration

| Setting | Value |
| --- | --- |
| Algorithm | PPO from Stable Baselines3 |
| Policy | MlpPolicy, shared between both agents |
| Agents | 2 |
| Observation | 8 values, four per agent: cwnd, smoothed RTT, loss placeholder, throughput |
| Action | Joint discrete, 25 values, five window actions per agent |
| Step interval | 100 ms |
| Episode | 60 simulated seconds, 599 learning steps |
| PPO hyperparameters | n_steps 2048, batch 64, 10 epochs, gamma 0.99 |
| Behaviour cloning | 3,000 steps, learning rate 1e-2 |
| PPO refinement | 3,000 steps, learning rate 5e-5, entropy coefficient 0.002 |

## Model files in the example directory

- `ppo_marl_multi_v4_bc.zip`: the behaviour-cloned policy before refinement.
- `ppo_marl_multi_v2.zip`: the final learned policy used in the evaluation.
- `ppo_marl_multi.zip`: the original invalid model, kept for the record.
- `ppo_marl_multi_v2_continuous.zip`, `ppo_marl_multi_v2_flood.zip`: earlier
  models kept for the record.

The two model files that matter are copied into
`docu/m4-marl-training/code/m4.3-marl-two-agents/`.

## Honest limitations

1. The loss input is a constant zero, so the loss term does not affect learning.
2. The imitation stage is not reinforcement learning by itself. It is a warm
   start. The final policy is refined by PPO, and both stages are documented.
3. The reward weights were chosen from constant-action measurements, not from a
   systematic search.
4. The topology is a single dumbbell with two identical flows. The policy was not
   tested against mixed algorithms, more flows, or wireless loss.

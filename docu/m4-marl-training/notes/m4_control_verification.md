# M4 control verification and reward calibration

Author: Okafor Kosisochukwu Johnpaul
Date: 3 October 2026

## The question this test answers

After I fixed the configuration ordering described in
`m4_root_cause_correction.md`, I did not want to trust the fix just because the
program printed the right class name. I wanted to see the congestion window
follow the actions. If the policy owns cwnd, then forcing the same action at
every step must push cwnd in a predictable direction. If ns-3's own congestion
control still owns cwnd, then the action has no steady effect and every constant
action produces nearly the same trace.

I wrote `rl_agent/verify_control.py` to run this test. It also records the reward
that the C++ environment computes. That second output turned out to be the most
important part of the work, because it showed that the reward in the submitted
report made "keep the window small" the best behaviour.

## How the test works

The script starts the multi-agent ns-3 program once per constant policy. Each
run uses the same topology, the same seed, and a duration of 15 seconds. The only
difference is the action sent at every step. The action space is the one in the
environment and in the report:

| Action value | Multiplier | Meaning |
| --- | --- | --- |
| 0 | 1.0 | keep cwnd |
| 1 | 1.1 | increase cwnd by 10 percent |
| 2 | 0.9 | decrease cwnd by 10 percent |
| 3 | 1.2 | increase cwnd by 20 percent |
| 4 | 0.8 | decrease cwnd by 20 percent |

Both agents receive the same constant action. The script records the raw
observation vector at every step. The vector for each agent is congestion window
in bytes, smoothed round trip time in milliseconds, a loss placeholder, and
throughput in bits per second. The script writes the raw traces to CSV files and
summarises them.

## Part 1: the actions own cwnd

Results from a 15 second run, summarised as the mean of the trace:

| Policy | Action | Mean cwnd of agent 0 | Mean total throughput | Final cwnd of agent 0 |
| --- | --- | --- | --- | --- |
| decrease 20 percent | 4 | 628 bytes | 71.9 kbps | 536 bytes |
| decrease 10 percent | 2 | 748 bytes | 108.2 kbps | 536 bytes |
| keep cwnd | 0 | 5,360 bytes | 1904.3 kbps | 5,360 bytes |
| increase 10 percent | 1 | 61,622 bytes | 6075.0 kbps | 237,105 bytes |
| increase 20 percent | 3 | 25,304,267 bytes | 8222.5 kbps | 626,098,176 bytes |

The traces separate in the way the action table predicts. Repeated decreases
collapse cwnd to a few hundred bytes and throughput falls with it. Repeated
increases grow cwnd and raise throughput.

The "keep cwnd" row is the clearest single piece of evidence. A native
loss-based algorithm such as CUBIC cannot hold a congestion window constant for
15 seconds. It grows the window on every acknowledgment and cuts it on loss, so
its cwnd trace is a sawtooth. An exactly constant 5,360 byte trace means no
native algorithm is changing cwnd. The only thing changing cwnd in the other
rows is the action.

## Part 2: the reward from the report prefers a small window

The same runs record the reward from the C++ environment. With the reward
formula in the submitted report, which gives throughput up to 20 points and
charges 1 point per millisecond of queueing delay, the mean reward per step was:

| Policy | Mean reward per step (report reward) |
| --- | --- |
| decrease 20 percent | -7.69 |
| decrease 10 percent | -5.89 |
| keep cwnd | 23.79 |
| increase 10 percent | 22.85 |
| increase 20 percent | 21.57 |

Keeping cwnd had the highest mean reward. Increasing the window raised
throughput but filled the queue, and a full 100 packet queue at 10 Mbps adds
about 120 to 240 ms of queueing delay. At 1 point per millisecond that costs 12
to 24 points, while the extra throughput is worth only a few points under the
old weights. The reward therefore preferred a small window.

## Part 3: my first corrected training run learned to hold cwnd

I trained the shared policy for about 30 minutes against the report reward. The
mean episode reward settled at about 14,000, which is 23.3 points per step. That
matches the "keep cwnd" row almost exactly. The policy had learned to hold cwnd
small. The reward was doing what it said; the specification was wrong for the
project goal.

The reward curve for that attempt is saved as
`marl_v2_training_rewards_attempt1.csv`.

## Part 4: the first reward change, and a second failure

I changed the reward to throughput up to 40 points, fairness up to 20, queueing
delay 0.1 points per millisecond, and loss 20 points per unit loss rate. I also
reordered the action values from the largest decrease to the largest increase so
that the middle of the action range meant "hold".

I ran the constant-action test again. The reward landscape over 15 seconds
became: hold 27.60, increase 10 percent 31.70, increase 20 percent 28.39. That
looked like an improvement, so I restarted training.

The training reward was about -6,250 per episode, which is -10.4 points per
step. That is worse than every constant policy I had measured, so I stopped and
investigated. The cause was the action reordering combined with how Stable
Baselines3 initialises its policy. The policy network starts with an output
mean near zero. The action space is a continuous box from 0 to 4. With the new
ordering, an output of zero means "decrease by 20 percent", so the untrained
policy began by shrinking cwnd. Once cwnd collapsed, many steps had zero
throughput for both agents. Jain fairness is zero when both flows deliver
nothing, so those steps lost the 20 point fairness term and kept the delay
penalty. Each such step scored about -19, and the policy settled into the
collapsed state.

I reverted the action ordering so that action 0 is "keep cwnd" again. Stable
Baselines3 therefore starts from a safe hold, and the exploration samples that
go above zero are increases.

The reward curve for that failed attempt is saved as
`marl_v2_training_rewards_attempt2_collapse.csv`.

## Part 5: the final reward balance

I kept the original action ordering and changed the weights again. Throughput is
now worth up to 60 points per step, fairness up to 20, queueing delay 0.05 points
per millisecond, and loss 20 points per unit loss rate. I also fixed a smaller
issue in the same function: a smoothed RTT of zero, which means no RTT sample
exists yet, was allowed to set the minimum RTT. That made the base propagation
delay count as queueing delay for the rest of the run. Zero samples are now
ignored.

Mean reward per step for the constant policies, 15 second runs:

| Policy | Action | Mean reward per step (final reward) |
| --- | --- | --- |
| decrease 20 percent | 4 | 0.88 |
| decrease 10 percent | 2 | 2.29 |
| keep cwnd | 0 | 31.41 |
| increase 10 percent | 1 | 44.96 |
| increase 20 percent | 3 | 44.94 |

Increasing is now worth about 14 points per step more than holding, so the
untrained policy, which starts at hold, has a clear reason to raise cwnd. The
full formula and the reasoning are in the comment above
`MyMultiGymEnv::GetReward` in `marl-multi-env.cc`.

## Files produced

- `docu/m5-evaluation/results/control_verification/control_summary.csv`
- `docu/m5-evaluation/results/control_verification/control_decrease20.csv`
- `docu/m5-evaluation/results/control_verification/control_decrease10.csv`
- `docu/m5-evaluation/results/control_verification/control_hold.csv`
- `docu/m5-evaluation/results/control_verification/control_increase10.csv`
- `docu/m5-evaluation/results/control_verification/control_increase20.csv`
- `docu/m5-evaluation/results/control_verification/control_verification.png`
- `docu/m4-marl-training/results/marl_v2_training_rewards_attempt1.csv`
- `docu/m4-marl-training/results/marl_v2_training_rewards_attempt2_collapse.csv`

## How to reproduce it

```bash
cd /home/ksschkw/Projects/fyp
venv/bin/python rl_agent/verify_control.py --duration 15
```

The script picks a free TCP port for each run, so it does not collide with other
processes. It changes into the `marl-multi-tcp` directory because ns3-gym takes
the ns-3 program name from the current directory name.

## Part 6: the final window charge, and the final reward landscape

The delay charge alone, even at 0.3 points per millisecond, did not pull the
policy away from raising the window at every step. I therefore added a direct
charge on the congestion window, 0.0005 points per byte per step, on top of the
delay charge. The final reward is

```
reward = 60 * min(total_throughput_mbps / 10, 1)
       + 20 * jain_fairness
       - 0.3 * average_queueing_delay_ms
       - 20 * average_loss_rate
       - 0.0005 * average_congestion_window_bytes
```

The constant-action test gives the following mean reward per step over 15
seconds:

| Constant action | Mean reward per step |
| --- | --- |
| decrease 20 percent | -40.82 |
| decrease 10 percent | -36.84 |
| hold | 28.71 |
| increase 10 percent | 0.25 |
| increase 20 percent | -8439.19 |

None of the constant actions is good, because a constant action either holds the
window at its small starting size or grows it without limit. A policy that raises
the window to the bandwidth-delay product and then holds it earns about 56 points
per step, which is higher than every constant action. The learned policy does
exactly that, and its result is in `m5_corrected_evaluation.md`.

## What this establishes

1. The RL action pipeline reaches the socket state and changes cwnd.
2. The native congestion control is not overwriting those changes.
3. The reward in the submitted report made "hold cwnd" the best behaviour, and a
   policy trained against it learned exactly that.
4. Several intermediate reward settings were measured and rejected. A delay
   charge alone either favoured holding a tiny window or allowed the policy to
   flood the queue. A direct window charge separates the good operating point
   from the flooding one.
5. The same test is the check that every trained policy is evaluated against: if
   the actions did not own cwnd, the constant actions could not produce these
   different traces.

# M4 v2: how to build, verify, train and evaluate the corrected environment

Author: Okafor Kosisochukwu Johnpaul
Date: 3 October 2026

This note lists the exact commands for the corrected multi-agent workflow. It
assumes the project is at `/home/ksschkw/Projects/fyp` and that Python runs
through the project virtual environment.

## 1. Rebuild the simulator

The no-op congestion control verification added a getter to the internet module,
so the internet library must be rebuilt and then the example.

```bash
cd /home/ksschkw/Projects/fyp/ns-3-dev
./ns3 build marl-multi-tcp
```

## 2. Verify that the RL policy owns the congestion window

```bash
cd /home/ksschkw/Projects/fyp
venv/bin/python rl_agent/verify_control.py --duration 15
```

Expected result: the program prints
`[MarlMulti] sender 0 congestion control = NoOpTcpCongestion` once per run, and
the five constant policies produce different cwnd traces. The "keep cwnd" policy
holds cwnd at a constant value instead of showing the CUBIC sawtooth.

Outputs go to `docu/m5-evaluation/results/control_verification/`.

## 3. Train the shared policy

```bash
cd /home/ksschkw/Projects/fyp
MARL_TIMESTEPS=100000 venv/bin/python -u rl_agent/train_marl_multi_v2.py
```

What the script does:

1. Changes into `ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp`, because
   ns3-gym takes the program name from the working directory name.
2. Creates the wrapped environment with `simArgs={"--flowmon": 0}`. FlowMonitor
   is disabled because it is expensive and only needed for evaluation.
3. Trains PPO with the same hyperparameters as the original run.
4. Saves a checkpoint every 10,000 steps as
   `ppo_marl_multi_v2_ckpt_<steps>_steps.zip`.
5. Writes every finished episode reward to
   `docu/m4-marl-training/results/marl_v2_training_rewards.csv`.
6. Saves the final model as `ppo_marl_multi_v2.zip`.

The old invalid model, `ppo_marl_multi.zip`, is left untouched for the record.

## 4. Evaluate

Baselines only:

```bash
venv/bin/python rl_agent/m5_evaluate.py --baselines --duration 60
```

Trained policy for three seeds, plus the baselines already on disk:

```bash
venv/bin/python rl_agent/m5_evaluate.py --marl --seeds 1 2 3 --duration 60
```

Rebuild the tables and plots from files already on disk:

```bash
venv/bin/python rl_agent/m5_evaluate.py --plot-only --marl
```

To evaluate a checkpoint instead of the final model, pass `--model`:

```bash
venv/bin/python rl_agent/m5_evaluate.py --marl --model \
  ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp/ppo_marl_multi_v2_ckpt_50000_steps.zip
```

Outputs go to `docu/m5-evaluation/results/`:

- `m5_corrected_summary.csv` and `.json`: one row per scenario.
- `m5_corrected_comparison.png`: four panel throughput, delay, loss, fairness.
- `marl_v2_seed<N>.flowmon`: FlowMonitor XML per seed.
- `marl_v2_seed<N>_cwnd.csv`: congestion window per step per seed.
- `marl_v2_cwnd_traces.png`: congestion window against time.

## 5. Generate a NetAnim file

After the `--anim` switch is present:

```bash
cd /home/ksschkw/Projects/fyp/ns-3-dev
./ns3 run "marl-multi-tcp --duration=5 --anim=1 --flowmon=1 --openGymPort=5555"
```

The Python side must be attached. The file is written as
`marl-multi-animation.xml` and is copied to
`docu/m5-evaluation/results/marl-multi-animation.xml`.

Open it with:

```bash
/home/ksschkw/Projects/fyp/netanim/build/netanim \
  /home/ksschkw/Projects/fyp/docu/m5-evaluation/results/marl-multi-animation.xml
```

See `docu/m6-final-documentation/notes/netanim-guide.md` for details.

## 6. Mirror the code into docu

```bash
cd /home/ksschkw/Projects/fyp
bash docu/sync_code.sh
```

## File map

| Live path | docu path |
| --- | --- |
| `ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp/marl-multi-sim.cc` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp/marl-multi-env.{h,cc}` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/marl_multi_env.py` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/train_marl_multi_v2.py` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/verify_control.py` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/m5_evaluate.py` | `docu/m5-evaluation/code/` |
| `ns-3-dev/src/internet/model/tcp-socket-base.{h,cc}` | `docu/m4-marl-training/code/m4.3-marl-two-agents/ns3-patches/` |
| `ns-3-dev/scratch/two-flow-baseline.cc` | `docu/m5-evaluation/code/` |

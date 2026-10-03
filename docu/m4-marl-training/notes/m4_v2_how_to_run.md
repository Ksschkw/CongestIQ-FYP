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

There are two training routes. The delivered policy comes from route B.

### Route A: PPO from random weights

```bash
cd /home/ksschkw/Projects/fyp
MARL_TIMESTEPS=100000 venv/bin/python -u rl_agent/train_marl_multi_v2.py
```

This trains PPO from random weights. On this reward and topology it converges
to a policy that raises the window at every step and floods the queue, so this
route is kept for the record rather than for the delivered model.

### Route B: imitation warm start, then PPO refinement

```bash
cd /home/ksschkw/Projects/fyp
MARL_BC_STEPS=3000 MARL_FINETUNE_STEPS=20000 venv/bin/python -u rl_agent/bc_warmstart.py
```

This runs three stages:

1. It collects demonstrations from the reference controller. The reference
   controller raises the window by 20 percent while it is below 25 KB and holds
   it otherwise. Random actions are used for part of each episode so that many
   window sizes are visited, and every visited state is labelled with the
   reference action. The data is saved as `bc_demonstrations.npz`.
2. It trains the policy network to imitate those labels. That is behaviour
   cloning, which is supervised learning.
3. It refines the cloned policy with PPO at a low learning rate.

The helper `rl_agent/finetune_marl.py` can refine any saved model:

```bash
MARL_START_MODEL=.../ppo_marl_multi_v4_bc.zip MARL_OUT_MODEL=ppo_marl_multi_v4 \
MARL_FINETUNE_STEPS=3000 venv/bin/python -u rl_agent/finetune_marl.py
```

The final model is copied to `ppo_marl_multi_v2.zip`, which is the name the
evaluation script uses. The cloning and refinement are described in
`m4_retrain_v2.md`.

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
| `rl_agent/bc_warmstart.py` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/finetune_marl.py` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/verify_control.py` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/make_animation.py` | `docu/m4-marl-training/code/m4.3-marl-two-agents/` |
| `rl_agent/m5_evaluate.py` | `docu/m5-evaluation/code/` |
| `ns-3-dev/src/internet/model/tcp-socket-base.{h,cc}` | `docu/m4-marl-training/code/m4.3-marl-two-agents/ns3-patches/` |
| `ns-3-dev/scratch/two-flow-baseline.cc` | `docu/m5-evaluation/code/` |

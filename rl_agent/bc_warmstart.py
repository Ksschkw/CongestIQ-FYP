#!/usr/bin/env python3
"""
bc_warmstart.py

Warm-start the multi-agent policy by imitating a simple reference controller,
then refine it with PPO.

Why this exists
---------------
Training PPO from random weights kept converging to a policy that raised the
window at every step. That policy fills the router queue and earns about 33
reward points per step. A simple reference controller that raises the window
until it reaches about 25 KB and then holds it earns about 73 points per step,
so the good operating point is reachable. PPO did not find it because the
categorical policy stopped exploring the other window actions.

This script collects demonstrations from the reference controller, trains the
policy network to imitate them with supervised learning, and then runs PPO from
that starting point. The result is still a reinforcement learning policy; the
demonstrations are only a starting point.

Usage:
    MARL_BC_STEPS=3000 MARL_FINETUNE_STEPS=30000 venv/bin/python -u rl_agent/bc_warmstart.py
"""

import os
import csv
import warnings
from collections import Counter

import numpy as np
import torch

warnings.filterwarnings("ignore")

REPO = "/home/ksschkw/Projects/fyp"
SIM_DIR = os.path.join(REPO, "ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp")
RESULT_DIR = os.path.join(REPO, "docu/m4-marl-training/results")
OUT_MODEL = "ppo_marl_multi_v4"
CKPT_PREFIX = "ppo_marl_multi_v4_ckpt"

os.chdir(SIM_DIR)

from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback  # noqa: E402
from marl_multi_env import MarlMultiEnv  # noqa: E402

# Reference controller: action 18 is "raise both windows by 20 percent",
# action 0 is "hold both windows".
INCREASE_BOTH = 18
HOLD_BOTH = 0
TARGET_CWND_BYTES = 25000


def reference_action(raw_obs):
    """Raise the window until it reaches the target, then hold it."""
    cwnd = float(raw_obs[0])
    return INCREASE_BOTH if cwnd < TARGET_CWND_BYTES else HOLD_BOTH


def collect_demonstrations(episodes, seed=1):
    """Collect (state, reference action) pairs across a wide range of states.

    If the reference controller is also the behaviour that generated the data,
    every increase transition comes from the same narrow starting state, and
    behaviour cloning overfits to it. The data collection therefore explores
    with random actions for part of each episode so that many different window
    sizes are visited, and labels every visited state with the action that the
    reference rule would choose for that state.
    """
    rng = np.random.default_rng(seed)
    env = MarlMultiEnv(port=5555, stepTime=0.1, startSim=True, simSeed=seed,
                       debug=False, simArgs={"--flowmon": 0})
    obs_list = []
    act_list = []
    cwnd_list = []
    for ep in range(episodes):
        obs, _ = env.reset()
        done = False
        step = 0
        while not done:
            raw = env.last_raw_obs
            label = reference_action(raw)
            obs_list.append(np.asarray(obs, dtype=np.float32).copy())
            act_list.append(label)
            cwnd_list.append(float(raw[0]))
            # Explore for the first part of the episode so that the window
            # sweeps across many sizes, then follow the reference rule.
            if step < 220:
                action = int(rng.integers(0, 25))
            else:
                action = label
            obs, _reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            step += 1
        print("  demonstration episode %d finished" % (ep + 1))
    env.close()
    cwnd_arr = np.asarray(cwnd_list)
    print("  cwnd coverage: min %.0f, median %.0f, max %.0f"
          % (cwnd_arr.min(), np.median(cwnd_arr), cwnd_arr.max()))
    obs_arr = np.asarray(obs_list, dtype=np.float32)
    act_arr = np.asarray(act_list, dtype=np.int64)
    dataset_path = os.path.join(RESULT_DIR, "bc_demonstrations.npz")
    np.savez(dataset_path, obs=obs_arr, actions=act_arr, cwnd=cwnd_arr)
    print("  saved demonstrations to %s" % dataset_path)
    return obs_arr, act_arr


def behaviour_clone(model, obs, acts, steps, batch_size=128, lr=1e-2):
    """Supervised update of the policy network to match the demonstrations.

    This optimises the policy head directly with cross entropy on the action
    logits. An earlier version used Stable Baselines3's ``evaluate_actions`` to
    obtain the log probability, but that path produced a near-constant output
    for this policy even though the same data is easy to fit with a direct
    forward pass, so the direct pass is used instead.
    """
    import torch.nn.functional as F

    obs_t = torch.as_tensor(obs, dtype=torch.float32)
    act_t = torch.as_tensor(acts, dtype=torch.long)
    optimizer = torch.optim.Adam(model.policy.parameters(), lr=lr)
    n = len(obs_t)

    increase_idx = np.where(acts == INCREASE_BOTH)[0]
    hold_idx = np.where(acts != INCREASE_BOTH)[0]
    print("  demonstration split: %d increase, %d hold"
          % (len(increase_idx), len(hold_idx)))

    losses = []
    for step in range(steps):
        # Build each batch from half increase and half hold transitions so that
        # the increase rule is not swamped by the much larger hold class.
        n_inc = batch_size // 2
        n_hold = batch_size - n_inc
        inc_batch = np.random.choice(increase_idx, size=n_inc, replace=True) if len(increase_idx) else []
        hold_batch = np.random.choice(hold_idx, size=n_hold, replace=True) if len(hold_idx) else []
        idx = torch.as_tensor(np.concatenate([inc_batch, hold_batch]), dtype=torch.long)
        features = model.policy.extract_features(obs_t[idx])
        latent_pi, _latent_vf = model.policy.mlp_extractor(features)
        logits = model.policy.action_net(latent_pi)
        loss = F.cross_entropy(logits, act_t[idx])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))
        if (step + 1) % 500 == 0:
            print("  BC step %5d  mean loss (last 500) %.4f" % (step + 1, np.mean(losses[-500:])))

    with torch.no_grad():
        features = model.policy.extract_features(obs_t)
        latent_pi, _ = model.policy.mlp_extractor(features)
        pred = model.policy.action_net(latent_pi).argmax(dim=1).numpy()
    overall = float((pred == acts).mean())
    inc_acc = float((pred[increase_idx] == acts[increase_idx]).mean()) if len(increase_idx) else 0.0
    print("  BC accuracy: overall %.3f, increase transitions %.3f" % (overall, inc_acc))
    return overall, inc_acc


class EpisodeRewardLogger(BaseCallback):
    def __init__(self, path):
        super().__init__(verbose=0)
        self.path = path
        self.rows = []

    def _on_step(self):
        for info in self.locals.get("infos", []) or []:
            ep = info.get("episode") if isinstance(info, dict) else None
            if ep is not None:
                self.rows.append([len(self.rows), float(ep["r"]), int(ep["l"])])
                with open(self.path, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["episode", "reward", "length"])
                    w.writerows(self.rows)
        return True


def main():
    bc_steps = int(os.environ.get("MARL_BC_STEPS", "3000"))
    finetune_steps = int(os.environ.get("MARL_FINETUNE_STEPS", "30000"))
    demo_episodes = int(os.environ.get("MARL_DEMO_EPISODES", "8"))

    dataset_path = os.path.join(RESULT_DIR, "bc_demonstrations.npz")
    if os.path.exists(dataset_path) and os.environ.get("MARL_REUSE_DEMOS", "1") == "1":
        print("Step 1: reuse saved demonstrations from %s" % dataset_path)
        data = np.load(dataset_path)
        obs, acts = data["obs"], data["actions"]
    else:
        print("Step 1: collect demonstrations from the reference controller.")
        obs, acts = collect_demonstrations(demo_episodes)
    print("  %d transitions, action counts %s"
          % (len(acts), Counter(acts.tolist()).most_common()))

    print("Step 2: behaviour-clone the policy network.")
    env = MarlMultiEnv(port=5555, stepTime=0.1, startSim=True, simSeed=1,
                       debug=False, simArgs={"--flowmon": 0})
    model = PPO("MlpPolicy", env, verbose=0, ent_coef=0.02,
                tensorboard_log=os.path.join(SIM_DIR, "ppo_marl_multi_v4_tb"))
    behaviour_clone(model, obs, acts, bc_steps)
    model.save(OUT_MODEL + "_bc")
    print("  saved the behaviour-cloned model as %s_bc.zip" % OUT_MODEL)

    print("Step 3: refine with PPO for %d steps." % finetune_steps)
    reward_csv = os.path.join(RESULT_DIR, "marl_v4_bc_finetune_rewards.csv")
    callbacks = [
        EpisodeRewardLogger(reward_csv),
        CheckpointCallback(save_freq=10000, save_path=SIM_DIR,
                           name_prefix=CKPT_PREFIX, verbose=1),
    ]
    model.learn(total_timesteps=finetune_steps, callback=callbacks, reset_num_timesteps=True)
    model.save(OUT_MODEL)
    env.close()

    logger = callbacks[0]
    if logger.rows:
        rewards = [r[1] for r in logger.rows]
        print("Captured %d episodes. First %.1f, last %.1f, max %.1f"
              % (len(rewards), rewards[0], rewards[-1], max(rewards)))
    print("Finished. Model saved as %s.zip" % OUT_MODEL)


if __name__ == "__main__":
    main()

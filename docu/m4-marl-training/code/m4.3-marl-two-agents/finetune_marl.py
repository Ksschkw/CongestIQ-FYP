#!/usr/bin/env python3
"""
finetune_marl.py

Continue training the shared policy after a reward change. The previous policy
learned to increase the window at every step, which filled the router queue. The
delay charge in the reward was increased, and this script adapts the existing
policy to the new reward instead of starting again from random weights.

Usage:
    MARL_FINETUNE_STEPS=40000 venv/bin/python -u rl_agent/finetune_marl.py
"""

import os
import csv
import warnings

warnings.filterwarnings("ignore")

REPO = "/home/ksschkw/Projects/fyp"
SIM_DIR = os.path.join(REPO, "ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp")
RESULT_DIR = os.path.join(REPO, "docu/m4-marl-training/results")
START_MODEL = os.environ.get("MARL_START_MODEL",
                             os.path.join(SIM_DIR, "ppo_marl_multi_v2.zip"))
OUT_MODEL = os.environ.get("MARL_OUT_MODEL", "ppo_marl_multi_v4")

os.chdir(SIM_DIR)

from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback  # noqa: E402
from marl_multi_env import MarlMultiEnv  # noqa: E402


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
    steps = int(os.environ.get("MARL_FINETUNE_STEPS", "40000"))

    env = MarlMultiEnv(port=5555, stepTime=0.1, startSim=True, simSeed=1,
                       debug=False, simArgs={"--flowmon": 0})

    model = PPO.load(START_MODEL, env=env)
    model.learning_rate = float(os.environ.get("MARL_FINETUNE_LR", "1e-4"))
    # A small entropy bonus keeps a little exploration during refinement. Too
    # large a bonus would push the policy away from its good starting point.
    model.ent_coef = float(os.environ.get("MARL_FINETUNE_ENT", "0.005"))

    reward_csv = os.path.join(RESULT_DIR, "marl_v4_finetune_rewards.csv")
    callbacks = [
        EpisodeRewardLogger(reward_csv),
        CheckpointCallback(save_freq=10000, save_path=SIM_DIR,
                           name_prefix="ppo_marl_multi_v4_ckpt", verbose=1),
    ]

    print("Fine-tuning the shared policy for %d steps with the revised reward." % steps)
    model.learn(total_timesteps=steps, callback=callbacks, reset_num_timesteps=True)
    model.save(OUT_MODEL)
    env.close()

    logger = callbacks[0]
    if logger.rows:
        rewards = [r[1] for r in logger.rows]
        print("Captured %d episodes. First %.1f, last %.1f, max %.1f"
              % (len(rewards), rewards[0], rewards[-1], max(rewards)))
    print("Fine-tuning finished. Model saved as %s.zip" % OUT_MODEL)


if __name__ == "__main__":
    main()

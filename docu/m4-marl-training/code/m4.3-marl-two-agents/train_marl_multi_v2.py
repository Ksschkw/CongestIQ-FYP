#!/usr/bin/env python3
"""
train_marl_multi_v2.py

Train the shared PPO policy for the two-agent TCP congestion control task in
the corrected environment, where the RL actions really own cwnd.

Differences from train_marl_multi.py:
  * FlowMonitor is disabled during training (it is only needed for evaluation),
    which reduces wall time per episode.
  * A checkpoint is saved every 10,000 steps, so a usable model exists even if
    training has to stop early.
  * Episode rewards are written to CSV continuously for live progress plots.
  * The model is saved as ppo_marl_multi_v2.zip so the old (invalid) model is
    kept intact for the record.
"""

import os
import csv
import warnings

warnings.filterwarnings("ignore")

REPO = "/home/ksschkw/Projects/fyp"
SIM_DIR = os.path.join(REPO, "ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp")
RESULT_DIR = os.path.join(REPO, "docu/m4-marl-training/results")
os.makedirs(RESULT_DIR, exist_ok=True)

# startSim=True launches "ns3 run marl-multi-tcp ..."; the program name is taken
# from the working directory, so we must be inside that directory.
os.chdir(SIM_DIR)

from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback  # noqa: E402
from marl_multi_env import MarlMultiEnv  # noqa: E402


class EpisodeRewardLogger(BaseCallback):
    """Write every finished episode's reward to CSV as training proceeds."""

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
    total_timesteps = int(os.environ.get("MARL_TIMESTEPS", "100000"))

    env = MarlMultiEnv(
        port=5555,
        stepTime=0.1,
        startSim=True,
        simSeed=1,
        debug=False,
        simArgs={"--flowmon": 0},
    )

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.02,
        tensorboard_log=os.path.join(SIM_DIR, "ppo_marl_multi_v2_tb"),
    )

    reward_csv = os.path.join(RESULT_DIR, "marl_v2_training_rewards.csv")
    callbacks = [
        EpisodeRewardLogger(reward_csv),
        CheckpointCallback(
            save_freq=10000,
            save_path=SIM_DIR,
            name_prefix="ppo_marl_multi_v2_ckpt",
            verbose=1,
        ),
    ]

    print("Starting MARL training in the corrected environment...")
    model.learn(total_timesteps=total_timesteps, callback=callbacks)
    model.save("ppo_marl_multi_v2")
    env.close()

    # Final reward history, from the live logger.
    logger = callbacks[0]
    if logger.rows:
        rewards = [r[1] for r in logger.rows]
        print("Captured %d episodes. First %.1f, last %.1f, max %.1f"
              % (len(rewards), rewards[0], rewards[-1], max(rewards)))
    else:
        print("No episode rewards captured; check the SB3 log output.")

    print("Training finished. Model saved as ppo_marl_multi_v2.zip")


if __name__ == "__main__":
    main()

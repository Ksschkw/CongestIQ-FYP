#!/usr/bin/env python3
"""
train_marl_multi_manual.py
Connects to an already-running marl-multi-tcp ns-3 simulation.
No subprocess; start ns-3 manually in a separate terminal.
"""
import warnings
warnings.filterwarnings("ignore")

from stable_baselines3 import PPO
from marl_multi_env import MarlMultiEnv

# ns-3 must already be running and waiting on port 5555
env = MarlMultiEnv(port=5555, stepTime=0.1, simSeed=1, debug=False)

model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    tensorboard_log="./ppo_marl_multi_manual/"
)

print("Starting MARL training (two agents, shared policy)...")
model.learn(total_timesteps=100000)
model.save("ppo_marl_multi_manual")

env.close()
print("Training finished. Model saved as ppo_marl_multi_manual.zip")
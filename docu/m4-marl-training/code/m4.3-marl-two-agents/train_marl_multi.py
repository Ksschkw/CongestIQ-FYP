#!/usr/bin/env python3
import os, warnings
warnings.filterwarnings("ignore")

# IMPORTANT: cd into the folder that matches the ns-3 program name
os.chdir("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp")

from stable_baselines3 import PPO
from marl_multi_env import MarlMultiEnv

# startSim=True will automatically launch "ns3 run marl-multi-tcp ..."
env = MarlMultiEnv(port=5555, stepTime=0.1, startSim=True, simSeed=1, debug=False)

model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    tensorboard_log="./ppo_marl_multi/"
)

print("Starting MARL training (two agents, shared policy)...")
model.learn(total_timesteps=100000)
model.save("ppo_marl_multi")

env.close()
print("Training finished. Model saved as ppo_marl_multi.zip")
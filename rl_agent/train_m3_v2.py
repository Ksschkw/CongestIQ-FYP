#!/usr/bin/env python3
"""Retrain with improved reward and longer training."""
import os, warnings
warnings.filterwarnings("ignore")

os.chdir("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/rl-tcp")

from stable_baselines3 import PPO
from ns3gym import ns3env
from reward_wrapper_v2 import CustomRewardWrapperV2

env = ns3env.Ns3Env(port=5555, stepTime=0.1, startSim=True, simSeed=1, simArgs={}, debug=False)
env = CustomRewardWrapperV2(env)

model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=200000)   # 4× longer training
model.save("ppo_rl_tcp_model_v2")

env.close()
print("Training finished. Model saved as ppo_rl_tcp_model_v2.zip")
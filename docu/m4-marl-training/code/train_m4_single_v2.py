import os, warnings
warnings.filterwarnings("ignore")

os.chdir("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-tcp")

from stable_baselines3 import PPO
from ns3gym import ns3env
from reward_wrapper_m4v2 import CustomRewardWrapperM4V2

env = ns3env.Ns3Env(port=5555, stepTime=0.1, startSim=True, simSeed=1, simArgs={}, debug=False)
env = CustomRewardWrapperM4V2(env)

model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=100000)
model.save("ppo_m4_single_v2")

env.close()
print("M4 single-agent v2 training finished. Model saved as ppo_m4_single_v2.zip")
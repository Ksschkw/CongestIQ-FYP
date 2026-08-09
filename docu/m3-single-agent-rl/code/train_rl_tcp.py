import warnings
warnings.filterwarnings("ignore")

from stable_baselines3 import PPO
from ns3gym import ns3env
from reward_wrapper import CustomRewardWrapper

# Connect to already-running ns-3
env = ns3env.Ns3Env(port=5555, stepTime=0.1, startSim=False, simSeed=1, simArgs={}, debug=False)
env = CustomRewardWrapper(env)

model = PPO("MlpPolicy", env, verbose=1)   # no tensorboard
model.learn(total_timesteps=50000)
model.save("ppo_rl_tcp_model")

env.close()
print("Training finished.")
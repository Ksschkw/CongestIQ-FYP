import time, subprocess
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from congestiq_env import CongestiqEnv

# Start ns-3
ns3_process = subprocess.Popen(
    ["./ns3", "run", "congestiq"],
    cwd="/home/ksschkw/Projects/fyp/ns-3-dev",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
time.sleep(3)

env = CongestiqEnv(port=5555)
check_env(env)  # optional

model = PPO("MlpPolicy", env, verbose=1, tensorboard_log="./ppo_congestiq/")
model.learn(total_timesteps=50000)
model.save("ppo_congestiq_model")

env.close()
ns3_process.terminate()
print("Training complete.")
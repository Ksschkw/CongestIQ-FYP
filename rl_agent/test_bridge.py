"""
Minimal agent to verify the ns3-gym bridge works.
Connects to the opengym-example environment.
"""
import time
import subprocess
from ns3gym import ns3env

# Start ns3 simulation in the background
ns3_process = subprocess.Popen(
    ["./ns3", "run", "opengym-example", "--openGymPort=5555"],
    cwd="/home/ksschkw/Projects/fyp/ns-3-dev",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
time.sleep(2)  # let ns-3 start

env = ns3env.Ns3Env(port=5555, stepTime=0.5, startSim=False, simSeed=0, simArgs={}, debug=False)
obs = env.reset()
print("Observation space:", env.observation_space)
print("Action space:", env.action_space)
print("Initial observation:", obs)

for i in range(10):
    action = env.action_space.sample()
    obs, reward, done, info = env.step(action)
    print(f"Step {i}: action={action}, reward={reward:.3f}, done={done}")

env.close()
ns3_process.terminate()
print("Bridge test successful!")
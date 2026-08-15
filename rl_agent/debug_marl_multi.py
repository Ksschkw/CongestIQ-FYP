#!/usr/bin/env python3
import subprocess, time, warnings
warnings.filterwarnings("ignore")

ns3_dir = "/home/ksschkw/Projects/fyp/ns-3-dev"

# Launch the multi-agent ns-3 program explicitly
ns3_proc = subprocess.Popen(
    ["./ns3", "run", "marl-multi-tcp --openGymPort=5555"],
    cwd=ns3_dir,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
time.sleep(3)  # let ns-3 start and bind

from ns3gym import ns3env

env = ns3env.Ns3Env(port=5555, stepTime=0.1, startSim=False, simSeed=1, simArgs={}, debug=False)
print("obs space:", env.observation_space)
print("action space:", env.action_space)
obs = env.reset()
print("obs length:", len(obs))
print("obs sample:", obs[:8])
env.close()
ns3_proc.terminate()
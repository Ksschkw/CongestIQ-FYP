import os, warnings
warnings.filterwarnings("ignore")
os.chdir("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-tcp")

from ns3gym import ns3env
env = ns3env.Ns3Env(port=5555, stepTime=0.1, startSim=True, simSeed=1, simArgs={}, debug=False)
obs = env.reset()
print("Initial obs:", obs)
for i in range(20):
    action = env.action_space.sample()
    obs, reward, done, info = env.step(action)
    print(f"Step {i}: action={action}, obs={obs}, reward={reward}")
    if done:
        break
env.close()
"""Evaluate M4 single-agent v2 against CUBIC from M2."""
import os, sys, warnings, numpy as np, matplotlib.pyplot as plt, glob, xml.etree.ElementTree as ET
warnings.filterwarnings("ignore")

import gymnasium as gym
from stable_baselines3 import PPO

def parse_flowmon(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    flows = []
    for fe in root.findall('.//Flow'):
        txb = fe.get('txBytes')
        if txb is None: continue
        txb = int(txb); rxb = int(fe.get('rxBytes') or 0)
        txp = int(fe.get('txPackets') or 0); lost = int(fe.get('lostPackets') or 0)
        t0 = float(fe.get('timeFirstTxPacket').replace('+','').replace('ns',''))
        t1 = float(fe.get('timeLastRxPacket').replace('+','').replace('ns',''))
        dur = max(t1 - t0, 1e-9) / 1e9
        rxp = txp - lost
        thr = (rxb * 8) / dur / 1000.0
        dsum = float(fe.get('delaySum').replace('+','').replace('ns',''))
        delay = dsum / (rxp * 1e6) if rxp > 0 else 0.0
        loss = lost / txp if txp > 0 else 0.0
        flows.append({'txBytes': txb, 'throughput_kbps': thr, 'mean_delay_ms': delay, 'loss_ratio': loss})
    if not flows: return None
    flows.sort(key=lambda f: f['txBytes'], reverse=True)
    return flows[0]

def main():
    os.chdir("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-tcp")

    from ns3gym import ns3env
    env = ns3env.Ns3Env(port=5555, stepTime=0.1, startSim=True, simSeed=1, simArgs={}, debug=False)

    class EvalEnv(gym.Env):
        def __init__(self, raw_env):
            self.env = raw_env
            self.observation_space = gym.spaces.Box(
                low=float(np.min(raw_env.observation_space.low)),
                high=float(np.max(raw_env.observation_space.high)),
                shape=raw_env.observation_space.shape, dtype=np.float32)
            self.action_space = gym.spaces.Discrete(raw_env.action_space.n)
        def reset(self, seed=None, options=None):
            obs = self.env.reset(); return obs, {}
        def step(self, action):
            if hasattr(action, 'item'):
                action = int(action.item())
            obs, reward, done, info = self.env.step(action)
            terminated = done; truncated = False
            return obs, reward, terminated, truncated, info
        def close(self): self.env.close()
    env = EvalEnv(env)

    model = PPO.load("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-tcp/ppo_m4_single_v2")
    print("M4 single-agent v2 model loaded. Running evaluation...")

    obs, _ = env.reset()
    done = False
    total_reward = 0.0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        total_reward += reward
    print(f"Episode finished. Total reward: {total_reward:.2f}")
    env.close()

    # Parse FlowMonitor
    xml_file = "/home/ksschkw/Projects/fyp/ns-3-dev/rl-single-flow.flowmon"
    if not os.path.exists(xml_file):
        xml_file = max(glob.glob("/home/ksschkw/Projects/fyp/ns-3-dev/*.flowmon"), key=os.path.getmtime, default=None)
    if not xml_file:
        print("No FlowMonitor file found.")
        return
    rl = parse_flowmon(xml_file)
    if not rl:
        print("Could not parse flow.")
        return

    print("\nRL Agent (M4 single v2) performance:")
    print(f"  Throughput: {rl['throughput_kbps']:.1f} kbps")
    print(f"  Mean Delay: {rl['mean_delay_ms']:.2f} ms")
    print(f"  Loss:       {rl['loss_ratio']*100:.2f}%")

    cubic_thr = 2745.0; cubic_del = 62.78; cubic_loss = 0.19
    print("\nCUBIC (from M2) performance:")
    print(f"  Throughput: {cubic_thr:.1f} kbps")
    print(f"  Mean Delay: {cubic_del:.2f} ms")
    print(f"  Loss:       {cubic_loss:.2f}%")

    # Chart
    labels = ['RL Agent (M4 v2)', 'CUBIC (M2)']
    throughputs = [rl['throughput_kbps'], cubic_thr]
    plt.bar(labels, throughputs, color=['green','orange'])
    plt.ylabel('Throughput (kbps)')
    plt.title('M4 Single-Agent v2 vs CUBIC Throughput')
    out_path = "/home/ksschkw/Projects/fyp/docu/m4-marl-training/results/m4_single_v2_comparison.png"
    plt.savefig(out_path); plt.close()
    print(f"\nChart saved to {out_path}")

if __name__ == "__main__":
    main()
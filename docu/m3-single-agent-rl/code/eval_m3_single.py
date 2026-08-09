#!/usr/bin/env python3
"""Evaluate RL agent on single flow and compare with M2 CUBIC numbers."""
import os, sys, warnings, time, numpy as np, matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

import gymnasium as gym
from stable_baselines3 import PPO

def parse_flowmon(xml_file):
    import xml.etree.ElementTree as ET
    tree = ET.parse(xml_file)
    root = tree.getroot()
    data_ids = set()
    classifier = root.find('Ipv4FlowClassifier')
    if classifier is not None:
        for fe in classifier.findall('Flow'):
            if fe.get('protocol') == '6' and fe.get('destinationPort') == '9':
                data_ids.add(int(fe.get('flowId')))
    flows = []
    stats = root.find('FlowStats')
    if stats is None: return flows
    for fe in stats.findall('Flow'):
        fid = int(fe.get('flowId'))
        if fid not in data_ids: continue
        tx_bytes = int(fe.get('txBytes'))
        rx_bytes = int(fe.get('rxBytes'))
        tx_pkts = int(fe.get('txPackets'))
        lost_pkts = int(fe.get('lostPackets'))
        t0_ns = float(fe.get('timeFirstTxPacket').replace('+','').replace('ns',''))
        t1_ns = float(fe.get('timeLastRxPacket').replace('+','').replace('ns',''))
        dur_ns = t1_ns - t0_ns
        if dur_ns <= 0: dur_ns = 1e-9
        dur_s = dur_ns / 1e9
        rx_pkts = tx_pkts - lost_pkts
        thr_kbps = (rx_bytes * 8) / dur_s / 1000.0
        delay_sum_ns = float(fe.get('delaySum').replace('+','').replace('ns',''))
        mean_delay_ms = (delay_sum_ns / (rx_pkts * 1e6)) if rx_pkts > 0 else 0.0
        loss_ratio = lost_pkts / tx_pkts if tx_pkts > 0 else 0.0
        flows.append({'flowId': fid, 'throughput_kbps': thr_kbps, 'mean_delay_ms': mean_delay_ms, 'loss_ratio': loss_ratio})
    return flows

def main():
    from ns3gym import ns3env
    env = ns3env.Ns3Env(port=5555, stepTime=0.1, startSim=True, simSeed=1, simArgs={}, debug=False)

    # wrap spaces
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
            obs, reward, done, info = self.env.step(action)
            terminated = done; truncated = False
            return obs, reward, terminated, truncated, info
        def close(self): self.env.close()
    env = EvalEnv(env)

    model = PPO.load("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/rl-tcp/ppo_rl_tcp_model")
    print("Model loaded. Running RL evaluation...")

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

    # Parse RL results
    xml_file = "/home/ksschkw/Projects/fyp/ns-3-dev/rl-single-flow.flowmon"
    if not os.path.exists(xml_file):
        print("FlowMonitor file not found. Did the simulation run?")
        return
    rl_flows = parse_flowmon(xml_file)
    if not rl_flows:
        print("No flows found.")
        return
    rl = rl_flows[0]
    print("\nRL Agent performance:")
    print(f"  Throughput: {rl['throughput_kbps']:.1f} kbps")
    print(f"  Mean Delay: {rl['mean_delay_ms']:.2f} ms")
    print(f"  Loss:       {rl['loss_ratio']*100:.2f}%")

    # M2 CUBIC numbers (from my M2 run, flow 2)
    cubic_throughput = 2745.0   # kbps
    cubic_delay = 62.78         # ms
    cubic_loss = 0.19           # %

    print("\nCUBIC (from M2) performance:")
    print(f"  Throughput: {cubic_throughput:.1f} kbps")
    print(f"  Mean Delay: {cubic_delay:.2f} ms")
    print(f"  Loss:       {cubic_loss:.2f}%")

    # Bar chart comparison
    labels = ['RL Agent', 'CUBIC (M2)']
    throughputs = [rl['throughput_kbps'], cubic_throughput]
    plt.bar(labels, throughputs, color=['blue','orange'])
    plt.ylabel('Throughput (kbps)')
    plt.title('M3.6: RL Agent vs CUBIC Throughput (single flow)')
    out_path = "/home/ksschkw/Projects/fyp/docu/m3-single-agent-rl/results/m3_comparison.png"
    plt.savefig(out_path)
    plt.close()
    print(f"\nComparison chart saved to {out_path}")

if __name__ == "__main__":
    main()
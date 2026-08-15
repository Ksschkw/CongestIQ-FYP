#!/usr/bin/env python3
"""
eval_marl_multi.py
Evaluate the trained multi-agent RL policy on two TCP flows sharing a bottleneck.
Compares against CUBIC/BBR from M2 and computes Jain fairness.
"""
import os, sys, warnings, numpy as np, matplotlib.pyplot as plt, glob, xml.etree.ElementTree as ET
warnings.filterwarnings("ignore")

import gymnasium as gym
from stable_baselines3 import PPO

# Import our wrapper (which normalises observations and rounds actions)
sys.path.insert(0, "/home/ksschkw/Projects/fyp/rl_agent")
from marl_multi_env import MarlMultiEnv


def parse_flowmon(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    flows = []
    for fe in root.findall('.//Flow'):
        txb = fe.get('txBytes')
        if txb is None:
            continue
        txb = int(txb)
        rxb = int(fe.get('rxBytes') or 0)
        txp = int(fe.get('txPackets') or 0)
        lost = int(fe.get('lostPackets') or 0)
        t0 = float(fe.get('timeFirstTxPacket').replace('+','').replace('ns',''))
        t1 = float(fe.get('timeLastRxPacket').replace('+','').replace('ns',''))
        dur = max(t1 - t0, 1e-9) / 1e9
        rxp = txp - lost
        thr = (rxb * 8) / dur / 1000.0
        dsum = float(fe.get('delaySum').replace('+','').replace('ns',''))
        delay = dsum / (rxp * 1e6) if rxp > 0 else 0.0
        loss = lost / txp if txp > 0 else 0.0
        flows.append({
            'txBytes': txb,
            'throughput_kbps': thr,
            'mean_delay_ms': delay,
            'loss_ratio': loss
        })
    if not flows:
        return []
    # sort by txBytes descending, assume two data flows are top two
    flows.sort(key=lambda f: f['txBytes'], reverse=True)
    return flows


def main():
    # Change to the marl-multi-tcp directory so ns3-gym auto-launches the right program
    os.chdir("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp")

    # Create wrapper with startSim=True
    env = MarlMultiEnv(port=5555, stepTime=0.1, startSim=True, simSeed=1, debug=False)

    # Load trained model
    # model = PPO.load("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp/ppo_marl_multi")
    model = PPO.load("/home/ksschkw/Projects/fyp/ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp/ppo_marl_multi.zip")
    print("MARL model loaded. Running evaluation episode...")

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

    # Find FlowMonitor XML
    xml_file = "/home/ksschkw/Projects/fyp/ns-3-dev/marl-multi-flowmon.xml"
    if not os.path.exists(xml_file):
        xml_file = max(glob.glob("/home/ksschkw/Projects/fyp/ns-3-dev/*.flowmon"), key=os.path.getmtime, default=None)
    if not xml_file:
        print("No FlowMonitor file found.")
        return

    flows = parse_flowmon(xml_file)
    if len(flows) < 2:
        print("Expected at least 2 data flows, found", len(flows))
        return

    # Take the two largest flows (RL agents)
    rl1 = flows[0]
    rl2 = flows[1]

    print("\nMARL Agent 1 performance:")
    print(f"  Throughput: {rl1['throughput_kbps']:.1f} kbps")
    print(f"  Mean Delay: {rl1['mean_delay_ms']:.2f} ms")
    print(f"  Loss:       {rl1['loss_ratio']*100:.2f}%")

    print("\nMARL Agent 2 performance:")
    print(f"  Throughput: {rl2['throughput_kbps']:.1f} kbps")
    print(f"  Mean Delay: {rl2['mean_delay_ms']:.2f} ms")
    print(f"  Loss:       {rl2['loss_ratio']*100:.2f}%")

    # Jain fairness between the two RL flows
    t1 = rl1['throughput_kbps']
    t2 = rl2['throughput_kbps']
    jain = (t1 + t2)**2 / (2 * (t1**2 + t2**2)) if (t1**2 + t2**2) > 0 else 0.0
    print(f"\nJain Fairness Index (RL vs RL): {jain:.4f}")

    # Compare with CUBIC/BBR from M2 (single numbers per flow not directly comparable, but we can show baseline total)
    # For now print aggregate MARL total vs M2 total CUBIC throughput
    marl_total = t1 + t2
    print(f"\nMARL total throughput: {marl_total:.1f} kbps")
    print(f"M2 CUBIC total throughput (2 CUBIC flows): approx 5500 kbps (2 x 2745)")

    # Generate comparison chart: per-agent throughput vs ideal 5Mbps
    labels = ['MARL Agent 1', 'MARL Agent 2', 'Ideal Fair Share']
    values = [t1, t2, 5000]
    plt.bar(labels, values, color=['green', 'blue', 'gray'])
    plt.ylabel('Throughput (kbps)')
    plt.title('MARL Two-Agent Throughput Comparison')
    out_path = "/home/ksschkw/Projects/fyp/docu/m4-marl-training/results/marl_multi_eval.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Chart saved to {out_path}")

    # Save fairness as text file
    with open("/home/ksschkw/Projects/fyp/docu/m4-marl-training/results/fairness.txt", "w") as f:
        f.write(f"Jain Fairness Index: {jain:.4f}\n")
        f.write(f"MARL Agent 1 throughput: {t1:.1f} kbps\n")
        f.write(f"MARL Agent 2 throughput: {t2:.1f} kbps\n")
    print("Fairness result saved.")


if __name__ == "__main__":
    main()
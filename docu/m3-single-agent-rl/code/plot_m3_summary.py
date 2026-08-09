#!/usr/bin/env python3
"""Generate comparison charts for M3 experiments."""
import matplotlib.pyplot as plt
import numpy as np

# Data from training logs and evaluations
versions = ['v1', 'v2', 'v3']
# Training reward final values (ep_rew_mean at last iteration)
train_final_rewards = [-165, -67.8, 2.87]
# Evaluation throughput (kbps) for RL
rl_throughput = [208.4, 209.1, 209.1]
rl_delay = [22.79, 22.81, 22.81]
rl_loss = [0.0, 0.0, 0.0]

# CUBIC from M2
cubic_throughput = 2745.0
cubic_delay = 62.78
cubic_loss = 0.19

# Bar chart: throughput RL v1, v2, v3 vs CUBIC
fig, ax = plt.subplots()
x = np.arange(len(versions)+1)
width = 0.35
bars_rl = ax.bar(x[:-1] - width/2, rl_throughput, width, label='RL Agent', color='blue')
bar_cubic = ax.bar(x[-1] + width/2, cubic_throughput, width, label='CUBIC', color='orange')
ax.set_ylabel('Throughput (kbps)')
ax.set_title('M3: Throughput Comparison Across Reward Versions')
ax.set_xticks(x)
ax.set_xticklabels(versions + ['CUBIC'])
ax.legend()
plt.tight_layout()
plt.savefig('/home/ksschkw/Projects/fyp/docu/m3-single-agent-rl/results/throughput_comparison_all.png')
plt.close()

# Bar chart: delay
fig, ax = plt.subplots()
bars_rl = ax.bar(x[:-1] - width/2, rl_delay, width, label='RL Agent', color='blue')
bar_cubic = ax.bar(x[-1] + width/2, cubic_delay, width, label='CUBIC', color='orange')
ax.set_ylabel('Mean Delay (ms)')
ax.set_title('M3: Delay Comparison Across Reward Versions')
ax.set_xticks(x)
ax.set_xticklabels(versions + ['CUBIC'])
ax.legend()
plt.tight_layout()
plt.savefig('/home/ksschkw/Projects/fyp/docu/m3-single-agent-rl/results/delay_comparison_all.png')
plt.close()

# Bar chart: loss
fig, ax = plt.subplots()
bars_rl = ax.bar(x[:-1] - width/2, rl_loss, width, label='RL Agent', color='blue')
bar_cubic = ax.bar(x[-1] + width/2, cubic_loss, width, label='CUBIC', color='orange')
ax.set_ylabel('Loss Ratio (%)')
ax.set_title('M3: Packet Loss Comparison Across Reward Versions')
ax.set_xticks(x)
ax.set_xticklabels(versions + ['CUBIC'])
ax.legend()
plt.tight_layout()
plt.savefig('/home/ksschkw/Projects/fyp/docu/m3-single-agent-rl/results/loss_comparison_all.png')
plt.close()

# Training reward progression for each version (simplified from logs)
# v1: iterations 1-25, rewards from output
v1_rewards = [-259, -256, -246, -239, -227, -219, -191, -187, -184, -181, -178, -176, -174, -173, -171, -170, -168, -168, -167, -166, -165, -165]
v2_rewards = [-5780, -5120, -4580, -4140, -3620, -3280, -2960, -2550, -2120, -1860, -1550, -1340, -1120, -985, -890, -790, -728, -681, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678, -678]
v3_rewards = [-262, -230, -202, -170, -149, -124, -109, -94.6, -78.1, -67.5, -55.3, -47.3, -40.1, -31.6, -25.9, -19.1, -14.4, -10.2, -5.01, -1.49, 2.87]

plt.figure()
plt.plot(range(1, len(v1_rewards)+1), v1_rewards, label='v1 (decaying-max)')
plt.plot(range(1, len(v2_rewards)+1), v2_rewards, label='v2 (direct throughput)')
plt.plot(range(1, len(v3_rewards)+1), v3_rewards, label='v3 (cwnd target)')
plt.xlabel('Iteration')
plt.ylabel('Average Episode Reward')
plt.title('M3: Training Reward Progression')
plt.legend()
plt.grid(True)
plt.savefig('/home/ksschkw/Projects/fyp/docu/m3-single-agent-rl/results/training_rewards_all.png')
plt.close()

print("All charts saved to docu/m3-single-agent-rl/results/")
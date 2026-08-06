import matplotlib.pyplot as plt

# Reward values from your training log (copy the ep_rew_mean values)
rewards = [-259, -256, -246, -239, -227, -219, -191, -187, -184, -181, -178, -176, -174, -173, -171, -170, -168, -168, -167, -166, -165, -165]
iterations = list(range(1, len(rewards)+1))

plt.plot(iterations, rewards, marker='o')
plt.xlabel('PPO Iteration')
plt.ylabel('Average Episode Reward')
plt.title('M3.5: Convergence of RL Agent')
plt.grid(True)
plt.savefig('convergence_m3.png')
plt.show()
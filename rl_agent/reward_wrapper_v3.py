import gymnasium
import numpy as np
from gymnasium import spaces

class CustomRewardWrapperV3(gymnasium.Env):
    """V3: reward cwnd close to BDP, penalise queueing delay and loss."""
    def __init__(self, ns3_env):
        super().__init__()
        self.env = ns3_env

        if hasattr(ns3_env.action_space, 'n'):
            self.action_space = spaces.Discrete(ns3_env.action_space.n)
        else:
            self.action_space = spaces.Box(
                low=ns3_env.action_space.low,
                high=ns3_env.action_space.high,
                dtype=np.float32)

        self.observation_space = spaces.Box(
            low=float(np.min(ns3_env.observation_space.low)),
            high=float(np.max(ns3_env.observation_space.high)),
            shape=ns3_env.observation_space.shape,
            dtype=np.float32)

        self.min_rtt = None          # physical delay
        self.target_cwnd = 25000.0   # BDP = 10 Mbps * 20 ms = 25 KB (approx)

    def step(self, action):
        obs, reward, done, info = self.env.step(action)
        terminated = done
        truncated = False
        reward = self._compute_reward(obs)
        return obs, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        obs = self.env.reset()
        self.min_rtt = None
        return obs, {}

    def _compute_reward(self, obs):
        cwnd, srtt, loss_rate, _ = obs[0], obs[1], obs[2], obs[3]   # ignore fake throughput

        # 1. Throughput proxy: reward cwnd near target, punish excess
        cwnd_kb = cwnd / 1000.0          # cwnd in KB
        target_kb = self.target_cwnd / 1000.0  # 25 KB
        # Use a Gaussian-like reward: max at target, falls off either side
        cwnd_reward = np.exp(-0.5 * ((cwnd_kb - target_kb) / (target_kb * 0.5)) ** 2)
        # Scale to ~1.0 at best

        # 2. Delay penalty: queueing delay in ms
        srtt_ms = srtt   # already in ms
        if self.min_rtt is None:
            self.min_rtt = srtt_ms
        else:
            self.min_rtt = min(self.min_rtt, srtt_ms)
        queue_delay = max(0.0, srtt_ms - self.min_rtt)
        delay_penalty = queue_delay / 50.0   # 50 ms queue = -1.0

        # 3. Loss penalty
        loss_penalty = loss_rate * 10.0

        reward = cwnd_reward - 0.5 * delay_penalty - 2.0 * loss_penalty
        return float(reward)

    def close(self):
        self.env.close()
import gymnasium
import numpy as np
from gymnasium import spaces

class CustomRewardWrapper(gymnasium.Env):
    """Wraps an old-Gym ns3 environment, converts spaces, and uses our reward."""
    def __init__(self, ns3_env):
        super().__init__()
        self.env = ns3_env

        # Convert action space
        if hasattr(ns3_env.action_space, 'n'):
            self.action_space = spaces.Discrete(ns3_env.action_space.n)
        else:
            self.action_space = spaces.Box(
                low=ns3_env.action_space.low,
                high=ns3_env.action_space.high,
                dtype=np.float32
            )

        # Convert observation space
        self.observation_space = spaces.Box(
            low=float(np.min(ns3_env.observation_space.low)),
            high=float(np.max(ns3_env.observation_space.high)),
            shape=ns3_env.observation_space.shape,
            dtype=np.float32
        )

        self.max_throughput = 1.0
        self.min_rtt = 1e9
        self.max_rtt = 1.0
        self.decay = 0.98

    def step(self, action):
        obs, reward, done, info = self.env.step(action)
        terminated = done
        truncated = False
        reward = self._compute_reward(obs)
        return obs, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        obs = self.env.reset()
        self.max_throughput = 1.0
        self.min_rtt = 1e9
        self.max_rtt = 1.0
        return obs, {}

    def _compute_reward(self, obs):
        cwnd, srtt, loss_rate, throughput = obs[0], obs[1], obs[2], obs[3]
        alpha, beta, gamma = 1.0, 0.5, 2.0

        self.max_throughput = max(throughput, self.max_throughput * self.decay)
        if self.max_throughput < 1.0:
            self.max_throughput = 1.0
        thr_reward = min(throughput / self.max_throughput, 1.0)

        self.min_rtt = min(srtt, self.min_rtt)
        self.max_rtt = max(srtt, self.max_rtt * self.decay)
        denom = self.max_rtt - self.min_rtt
        if denom < 1e-9:
            delay_pen = 0.0
        else:
            delay_pen = (srtt - self.min_rtt) / denom
            delay_pen = max(0.0, min(delay_pen, 1.0))

        loss_pen = loss_rate
        reward = alpha * thr_reward - beta * delay_pen - gamma * loss_pen
        return float(reward)

    def close(self):
        self.env.close()
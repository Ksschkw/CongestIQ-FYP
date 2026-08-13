import gymnasium
import numpy as np
from gymnasium import spaces

class CustomRewardWrapperM4V2(gymnasium.Env):
    """M4 reward v2: heavily reward throughput, penalise queueing delay and loss."""
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

        self.bottleneck_mbps = 10.0
        self.min_rtt = None

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
        cwnd, srtt, loss_rate, throughput_bps = obs[0], obs[1], obs[2], obs[3]

        # Throughput reward: 0..20
        throughput_mbps = throughput_bps / 1_000_000.0
        thr_reward = min(throughput_mbps / self.bottleneck_mbps, 1.0) * 20.0

        # Delay penalty: 10 ms queueing = -1.0
        rtt_ms = srtt
        if self.min_rtt is None:
            self.min_rtt = rtt_ms
        else:
            self.min_rtt = min(self.min_rtt, rtt_ms)
        queue_delay_ms = max(0.0, rtt_ms - self.min_rtt)
        delay_pen = queue_delay_ms / 10.0

        # Loss penalty: 1% loss = -0.2
        loss_pen = loss_rate * 20.0

        reward = thr_reward - delay_pen - loss_pen
        return float(reward)

    def close(self):
        self.env.close()
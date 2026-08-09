import gymnasium
import numpy as np
from gymnasium import spaces

class CustomRewardWrapperV2(gymnasium.Env):
    """Revised reward: reward throughput directly, punish delay/loss mildly."""
    def __init__(self, ns3_env):
        super().__init__()
        self.env = ns3_env

        if hasattr(ns3_env.action_space, 'n'):
            self.action_space = spaces.Discrete(ns3_env.action_space.n)
        else:
            self.action_space = spaces.Box(
                low=ns3_env.action_space.low,
                high=ns3_env.action_space.high,
                dtype=np.float32
            )

        self.observation_space = spaces.Box(
            low=float(np.min(ns3_env.observation_space.low)),
            high=float(np.max(ns3_env.observation_space.high)),
            shape=ns3_env.observation_space.shape,
            dtype=np.float32
        )

        # Track only min RTT for queueing delay calculation
        self.min_rtt = None   # will be initialised on first step

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

        # Throughput reward: directly use throughput in Mbps (0.1–10)
        throughput_mbps = throughput_bps / 1e6
        thr_reward = throughput_mbps   # up to ~10

        # Delay penalty: queueing delay in seconds, mild penalty
        # srtt is in milliseconds, convert to seconds
        rtt_sec = srtt / 1000.0
        if self.min_rtt is None:
            self.min_rtt = rtt_sec
        else:
            self.min_rtt = min(self.min_rtt, rtt_sec)
        queueing_delay = max(0.0, rtt_sec - self.min_rtt)
        delay_pen = queueing_delay * 100.0   # scale so 10ms queue = 1.0 penalty

        # Loss penalty: weight 5.0, but loss_rate is already 0-1
        loss_pen = loss_rate * 5.0

        reward = thr_reward - delay_pen - loss_pen
        return float(reward)

    def close(self):
        self.env.close()
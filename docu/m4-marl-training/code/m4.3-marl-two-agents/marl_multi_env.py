#!/usr/bin/env python3
"""
marl_multi_env.py
Python wrapper for ns-3 multi-agent TCP environment (Option A).
Normalises observations to avoid extreme values and NaN.
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from ns3gym import ns3env


class MarlMultiEnv(gym.Env):
    def __init__(self, port=5555, stepTime=0.1, startSim=True, simSeed=1, debug=False):
        super().__init__()

        # self.raw_env = ns3env.Ns3Env(
        #     port=port,
        #     stepTime=stepTime,
        #     startSim=False,
        #     simSeed=simSeed,
        #     simArgs={},
        #     debug=debug
        # )
        self.raw_env = ns3env.Ns3Env(
            port=port,
            stepTime=stepTime,
            startSim=startSim,
            simSeed=simSeed,
            simArgs={},
            debug=debug
        )

        # Infer number of agents from observation space shape
        raw_shape = self.raw_env.observation_space.shape
        total_dim = int(raw_shape[0]) if len(raw_shape) == 1 else int(np.prod(raw_shape))
        self.obs_dim = total_dim
        self.n_agents = total_dim // 4

        if self.n_agents == 0:
            raise RuntimeError("Observation dimension too small to infer agents")

        # Normalised observation space: all values roughly 0..1
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(self.obs_dim,),
            dtype=np.float32
        )

        # Continuous action space, one per agent, values 0..4. We'll round.
        self.action_space = spaces.Box(
            low=0.0,
            high=4.0,
            shape=(self.n_agents,),
            dtype=np.float32
        )

        # Scaling constants for normalisation
        self.cwnd_scale = 1e6        # max cwnd ~1 MB
        self.rtt_scale = 1000.0      # max RTT ~1000 ms
        self.loss_scale = 1.0        # already 0..1
        self.thr_scale = 1e7         # max throughput ~10 Mbps = 1e7 bps

        self.current_obs = None

    def _normalise_obs(self, obs):
        obs = np.asarray(obs, dtype=np.float32).flatten()
        # Replace any non-finite values with 0
        obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)

        normalised = np.zeros_like(obs, dtype=np.float32)
        for i in range(self.n_agents):
            base = i * 4
            normalised[base + 0] = obs[base + 0] / self.cwnd_scale  # cwnd
            normalised[base + 1] = obs[base + 1] / self.rtt_scale  # RTT
            normalised[base + 2] = obs[base + 2] / self.loss_scale  # loss
            normalised[base + 3] = obs[base + 3] / self.thr_scale  # throughput

        # Clip to [0,1]
        return np.clip(normalised, 0.0, 1.0)

    def reset(self, seed=None, options=None):
        raw_obs = self.raw_env.reset()
        self.current_obs = self._normalise_obs(raw_obs)
        return self.current_obs, {}

    def step(self, action):
        # Round continuous action to integer and clip to 0..4
        discrete_action = np.clip(np.rint(action), 0, 4).astype(np.uint32)

        raw_obs, reward, done, info = self.raw_env.step(discrete_action)

        terminated = done
        truncated = False

        self.current_obs = self._normalise_obs(raw_obs)
        reward = float(np.nan_to_num(reward, nan=0.0, posinf=0.0, neginf=0.0))

        return self.current_obs, reward, terminated, truncated, info

    def close(self):
        self.raw_env.close()
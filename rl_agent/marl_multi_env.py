#!/usr/bin/env python3
"""
marl_multi_env.py

Python wrapper for the ns-3 multi-agent TCP environment.

The C++ side exposes eight raw observation values, four per agent: congestion
window, smoothed round trip time, a loss placeholder, and throughput. This
wrapper normalises them into bounded ranges so that PPO receives inputs of
similar magnitude, and it forwards the joint discrete action back to ns-3.

The joint action space has five window actions per agent, so for two agents it
has 25 values. Agent 0 is the least significant digit of the joint value.
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from ns3gym import ns3env


class MarlMultiEnv(gym.Env):
    def __init__(self, port=5555, stepTime=0.1, startSim=True, simSeed=1, debug=False,
                 simArgs=None):
        super().__init__()

        # Extra command-line arguments forwarded to the ns-3 program,
        # for example {"--flowmon": 0, "--duration": 60}. FlowMonitor is
        # only needed for evaluation, so training turns it off.
        self.simArgs = dict(simArgs) if simArgs else {}

        self.raw_env = ns3env.Ns3Env(
            port=port,
            stepTime=stepTime,
            startSim=startSim,
            simSeed=simSeed,
            simArgs=self.simArgs,
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

        # Joint discrete action space. Each agent has five window actions, so
        # the joint space has 5^n_agents values. Agent 0 is the least
        # significant digit in the joint value. The C++ environment decodes the
        # joint value and applies one multiplier per agent.
        self.action_space = spaces.Discrete(5 ** self.n_agents)

        # Scaling constants for normalisation.
        #
        # The congestion window uses a saturating transform instead of a linear
        # scale. A linear scale with a fixed maximum clips once the window grows
        # past that maximum, and a policy that floods the queue can then no
        # longer see how far it has overshot, so it cannot learn to back off.
        # The saturating transform keeps every window size distinguishable:
        # 5 KB maps to about 0.09, 25 KB to 0.33, 100 KB to 0.67, and 1 MB to
        # 0.95. The raw observation is kept as last_raw_obs so that the
        # evaluation can report the true window in bytes.
        self.cwnd_saturation = 5.0e4   # bytes
        self.cwnd_scale = 1e5          # kept for reporting
        self.rtt_scale = 300.0         # base RTT is 40 ms, queueing pushes it higher
        self.loss_scale = 1.0          # already 0..1
        self.thr_scale = 1e7           # max throughput ~10 Mbps = 1e7 bps

        self.current_obs = None
        self.last_raw_obs = None

    def _normalise_obs(self, obs):
        obs = np.asarray(obs, dtype=np.float32).flatten()
        # Replace any non-finite values with 0
        obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)
        self.last_raw_obs = obs.copy()

        normalised = np.zeros_like(obs, dtype=np.float32)
        for i in range(self.n_agents):
            base = i * 4
            cwnd = obs[base + 0]
            normalised[base + 0] = cwnd / (cwnd + self.cwnd_saturation)  # cwnd
            normalised[base + 1] = obs[base + 1] / self.rtt_scale         # RTT
            normalised[base + 2] = obs[base + 2] / self.loss_scale        # loss
            normalised[base + 3] = obs[base + 3] / self.thr_scale         # throughput

        # Clip to [0,1]
        return np.clip(normalised, 0.0, 1.0)

    def reset(self, seed=None, options=None):
        raw_obs = self.raw_env.reset()
        self.current_obs = self._normalise_obs(raw_obs)
        return self.current_obs, {}

    def step(self, action):
        # The action is already a joint integer for the Discrete action space.
        raw_obs, reward, done, info = self.raw_env.step(int(action))

        terminated = done
        truncated = False

        self.current_obs = self._normalise_obs(raw_obs)
        reward = float(np.nan_to_num(reward, nan=0.0, posinf=0.0, neginf=0.0))

        return self.current_obs, reward, terminated, truncated, info

    def close(self):
        self.raw_env.close()
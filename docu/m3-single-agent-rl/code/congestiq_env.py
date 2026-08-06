import gymnasium
import numpy as np
import zmq
import ns3gym.messages_pb2 as pb

class CongestiqEnv(gymnasium.Env):
    metadata = {'render_modes': ['human']}
    
    def __init__(self, port=5555, debug=False):
        super().__init__()
        self.port = port
        self.debug = debug
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        
        self._init_ns3()
        
        self.action_space = gymnasium.spaces.Discrete(5)
        self.observation_space = gymnasium.spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0]),
            high=np.array([1e6, 1e6, 1.0, 1e6]),
            dtype=np.float32
        )
        
        # Reward trackers (decaying maximums)
        self.max_throughput = 1.0
        self.min_rtt = 1e9
        self.max_rtt = 1.0
        self.decay = 0.98
        
        self.done = False
    
    def _init_ns3(self):
        msg = self.socket.recv()
        simInit = pb.SimInitMsg()
        simInit.ParseFromString(msg)
        ack = pb.SimInitAck()
        ack.done = True
        ack.stopSimReq = False
        self.socket.send(ack.SerializeToString())
    
    def _recv_state(self):
        msg = self.socket.recv()
        stateMsg = pb.EnvStateMsg()
        stateMsg.ParseFromString(msg)
        self.done = stateMsg.isGameOver
        obs_data = stateMsg.obsData
        box = pb.BoxDataContainer()
        obs_data.data.Unpack(box)
        obs = np.array(box.floatData, dtype=np.float32)
        return obs, {}
    
    def _send_action(self, action):
        actMsg = pb.EnvActMsg()
        disc = pb.DiscreteDataContainer()
        disc.data = action
        actMsg.actData.type = pb.Discrete
        actMsg.actData.data.Pack(disc)
        actMsg.stopSimReq = False
        self.socket.send(actMsg.SerializeToString())
    
    def _compute_custom_reward(self, obs):
        cwnd, sRtt, loss_rate, throughput = obs[0], obs[1], obs[2], obs[3]
        alpha, beta, gamma = 1.0, 0.5, 2.0

        self.max_throughput = max(throughput, self.max_throughput * self.decay)
        if self.max_throughput < 1.0:
            self.max_throughput = 1.0
        thr_reward = min(throughput / self.max_throughput, 1.0)

        self.min_rtt = min(sRtt, self.min_rtt)
        self.max_rtt = max(sRtt, self.max_rtt * self.decay)
        denom = self.max_rtt - self.min_rtt
        if denom < 1e-9:
            delay_pen = 0.0
        else:
            delay_pen = (sRtt - self.min_rtt) / denom
            delay_pen = max(0.0, min(delay_pen, 1.0))

        loss_pen = loss_rate
        reward = alpha * thr_reward - beta * delay_pen - gamma * loss_pen
        return reward
    
    def step(self, action):
        self._send_action(action)
        obs, _ = self._recv_state()
        reward = self._compute_custom_reward(obs)
        return obs, reward, self.done, False, {}
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.max_throughput = 1.0
        self.min_rtt = 1e9
        self.max_rtt = 1.0
        obs, _ = self._recv_state()
        self.done = False
        return obs, {}
    
    def close(self):
        self.socket.close()
        self.context.term()
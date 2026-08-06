"""
Simple script to verify the ns3-gym ZMQ bridge.
Run this script FIRST in one terminal.
Then in another terminal, start the ns-3 simulation.
"""
import zmq
import time
import sys

port = 5555

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind(f"tcp://*:{port}")

print(f"[Python] Waiting for ns-3 to connect on port {port}...")
print(f"[Python] Now run this in another terminal:")
print(f"        cd ~/Projects/fyp/ns-3-dev && ./ns3 run \"opengym-example --openGymPort={port}\"")
sys.stdout.flush()

# 1) Receive SimInitMsg from ns-3
msg = socket.recv()
print(f"[Python] Received SimInitMsg ({len(msg)} bytes)")

# 2) Send SimInitAck
import ns3gym.messages_pb2 as pb
simInitMsg = pb.SimInitMsg()
simInitMsg.ParseFromString(msg)
print(f"[Python] ns-3 PID: {simInitMsg.simProcessId}")
print(f"[Python] Observation space: {simInitMsg.obsSpace}")
print(f"[Python] Action space: {simInitMsg.actSpace}")

reply = pb.SimInitAck()
reply.done = True
reply.stopSimReq = False
socket.send(reply.SerializeToString())
print("[Python] Sent SimInitAck")

# 3) Loop: receive EnvStateMsg, send random action
for step in range(10):
    msg = socket.recv()
    envStateMsg = pb.EnvStateMsg()
    envStateMsg.ParseFromString(msg)
    
    obs = envStateMsg.obsData
    reward = envStateMsg.reward
    done = envStateMsg.isGameOver
    print(f"[Python] Step {step}: reward={reward:.3f}, done={done}")

    if done:
        break

    # Send a random discrete action (the example action space is discrete(5))
    action = 2  # fixed action for test
    actMsg = pb.EnvActMsg()
    discContainer = pb.DiscreteDataContainer()
    discContainer.data = action
    actMsg.actData.type = pb.Discrete
    actMsg.actData.data.Pack(discContainer)
    actMsg.stopSimReq = False
    socket.send(actMsg.SerializeToString())

# Close
socket.close()
context.term()
print("[Python] Bridge test completed successfully!")
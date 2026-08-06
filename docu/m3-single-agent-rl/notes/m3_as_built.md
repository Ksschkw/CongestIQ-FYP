# M3 As‑Built – Single‑Agent RL Environment

**Date:** 06 August 2026  
**Author:** Okafor Kosisochukwu Johnpaul

---

## What This Milestone Was Supposed to Be

I planned to:

- Set up ns3‑gym so Python and ns‑3 can talk
- Build a custom Gymnasium environment with my own state, action, and reward
- Train a PPO agent that controls one TCP flow on a dumbbell
- See the reward improve over time

On paper it looked straightforward. Reality was… different.

---

## The Real Journey

### The ns3‑gym War

Getting ns3‑gym to compile took almost two weeks. The module wouldn't configure because of name clashes (`opengym` target already existing), missing protobuf generated files, and CMake not finding the right headers. I had to:

- Clone ns3‑gym into `contrib/ns3-gym`, switch to the `app‑ns‑3.36+` branch
- Manually generate `messages.pb.h` and `messages.pb.cc` with `protoc`
- Patch the CMakeLists.txt to include `messages.pb.cc` and disable broken examples (rl‑tcp initially, then others)
- Fix an override of `GetInstanceTypeId` that my newer ns‑3 no longer allowed
- Uncomment the constructor of `TcpSocketDerived` which was commented out for some reason

After countless `./ns3 configure --enable-examples && ./ns3 build` cycles, the `opengym` library and the `rl‑tcp` example finally compiled.

### The Python Bridge

The Python side had its own problems:

- `ns3gym` module needed `protobuf==3.20.3`, but I accidentally upgraded to 7.x when installing tensorboard, breaking the ZMQ connection completely. I had to downgrade back and skip tensorboard.
- The original `Ns3Env` uses old Gym spaces, while Stable‑Baselines3 requires Gymnasium spaces. I had to write a wrapper (`reward_wrapper.py`) that converts spaces and provides my custom reward.
- The deadlock: both Python and ns‑3 were waiting for each other. I learned that the correct flow is to let Python start ns‑3 via `startSim=True` (which the original `test.py` did).

### The Reward Function Evolution

I started with a hardcoded‑normalisation reward, but after discussion I realised it would overfit to my exact bottleneck. I switched to a **decaying‑maximum** scheme:

- Throughput reward is normalised by the maximum throughput seen so far (with decay 0.98), so the agent is rewarded relative to what it has actually achieved.
- Delay penalty uses `(currentRTT – minRTT) / (maxRTT – minRTT)`, where maxRTT decays. This prevents the agent from exploiting an early spike to permanently dilute future penalties.
- Loss penalty is simply the loss rate, with a weight of 2.0 (reduced from 10.0 to avoid a “reward cliff” that would make the agent afraid to send anything).
- The reward is computed in Python inside the wrapper, because the C++ side just passes raw metrics.

---

## Training Results

I trained PPO for 50,000 timesteps on a single 10 Mbps dumbbell flow (no competitor yet). The average episode reward went from **‑259** (iteration 1) to **‑165** (iteration 25), a 36% improvement. The reward is still negative because my reward function has penalties for delay and loss that outweigh the throughput gain on a congested link. The important thing is that it **improved**, meaning the agent learned to make better decisions.

I saved the trained model as `ppo_rl_tcp_model.zip`.

---

## What Actually Worked (and What Didn't)

### Worked
- The ZMQ bridge after protobuf fix
- The time‑based RL environment (`TcpRlTimeBased`) – it steps every 100 ms and gives me 4 observations (cwnd, sRTT, loss_rate placeholder, throughput)
- The decaying‑maximum reward wrapper
- Training with PPO from Stable‑Baselines3

### Did NOT work
- My original custom C++ environment (`congestiq‑sim.cc` and `my‑gym‑env.cc`) – too many API mismatches. I abandoned it in favour of modifying the existing `rl‑tcp` example.
- Event‑based RL (`TcpRl`) – it interfered with the time‑step logic I needed
- Direct `check_env` call – old Gym spaces caused assertion errors, so I removed it from the training script

---

## Files That Matter

- `contrib/ns3-gym/examples/rl-tcp/sim.cc` – my dumbbell topology (one RL flow for now)
- `contrib/ns3-gym/examples/rl-tcp/tcp-rl-env.h/cc` – the gym environment on the C++ side (modified to output 4‑float observation and 5 discrete actions)
- `rl_agent/reward_wrapper.py` – the Gymnasium wrapper that applies my decaying‑max reward
- `rl_agent/train_m3.py` – the training script
- `ppo_rl_tcp_model.zip` – the saved policy

---

## Next

Now I will add a second CUBIC flow to the dumbbell and compare the RL agent's performance against CUBIC (M3.6). Then I'll document the final observations and record the video.
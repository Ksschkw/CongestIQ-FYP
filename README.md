# CongestiQ – MARL for Adaptive TCP Congestion Control

> **Final‑year project by Kosichukwu Okafor (FUTO, Software Engineering)**  
> Investigating whether Multi‑Agent Reinforcement Learning can learn better congestion control than Reno, CUBIC, and BBR — all inside a simulator.

[![GitHub last commit](https://img.shields.io/github/last-commit/Ksschkw/CongestiQ-FYP.)](https://github.com/Ksschkw/CongestiQ-FYP.)
[![YouTube Playlist](https://img.shields.io/badge/YouTube-Playlist-red)](https://youtube.com/playlist?list=PLhU0J79Smu6kmr6QNJgd0cFa2f-UCwU1K)
[Read ](yada.md)
---

## Table of Contents

- [What is CongestiQ?](#what-is-congestiq)
- [Repository Structure](#repository-structure)
- [Milestones](#milestones)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Key Findings](#key-findings)
- [Documentation (the `docu/` folder)](#documentation)
- [Author](#author)
- [Acknowledgements](#acknowledgements)

---

## What is CongestiQ?

**CongestiQ** is a simulation‑based research platform that replaces traditional TCP congestion‑control algorithms (Reno, CUBIC, BBR) with a **Reinforcement Learning agent**. The agent learns to adjust the congestion window by interacting with a realistic network inside the **ns‑3** simulator.

### Why simulation, not real Linux TCP?

- **Safety** – Untrained RL policies could crash a real network.
- **Reproducibility** – Every experiment runs in an identical, controlled environment.
- **Speed** – Training happens in accelerated simulation time, not real‑time ACK intervals.

### Core design decisions

| Decision | Rationale |
|----------|-----------|
| **Offline training, frozen policy** | RL is too slow for per‑ACK decisions; we train in simulation, then evaluate. |
| **Multi‑Agent RL (MARL) with CTDE** | Multiple flows learn to share the bottleneck fairly (Centralised Training, Decentralised Execution). |
| **Periodic actions (once per RTT)** | Balances learning speed with realistic deployment constraints. |
| **Discrete action space** | Maintain, ±10%, ±20% of current cwnd – simple and explainable. |
| **Dynamic reward with decaying maximums** | Avoids over‑fitting to a single bottleneck capacity or buffer size. |
| **ns3‑gym bridge** | Python RL agents talk to ns‑3 via ZMQ and Protobuf. |

---

## Repository Structure

```
CongestiQ-FYP/
├── docu/                          ← All project documentation, notes, and results
│   ├── m1-network-sandbox/        ← M1: Reno vs CUBIC
│   ├── m2-congestion-dynamics/    ← M2: Multi‑flow analysis
│   ├── m3-single-agent-rl/        ← M3: RL environment and training
│   ├── m4-marl-training/          ← (future) Multi‑agent RL
│   ├── m5-evaluation/             ← (future) Full benchmarks
│   └── m6-final-documentation/    ← (future) Thesis chapters
├── ns-3-dev/                      ← ns‑3 simulator (gitignored)
├── netanim/                       ← NetAnim visualiser (gitignored)
├── rl_agent/                      ← Python RL code (reward wrappers, training/eval scripts)
├── .gitignore
└── README.md                      ← This file
```

Everything you need to understand, reproduce, or evaluate my work lives inside `docu/`. Each milestone sub‑folder contains:

- `code/` – all source files (C++ simulation scripts, Python agents, modified ns‑3 modules)  
- `results/` – graphs (PNG), FlowMonitor XML, NetAnim screenshots  
- `notes/` – detailed observations, as‑built narratives, experiment logs, video scripts  
- `videos/` – links to YouTube walkthroughs

---

## Milestones

| ID | Milestone | Status |
|----|-----------|--------|
| M1 | Network Sandbox | ✅ |
| M2 | Congestion Dynamics | ✅ |
| M3 | Single‑Agent RL | ✅ |
| M4 | MARL Training | 🔲 |
| M5 | Full Evaluation | 🔲 |
| M6 | Documentation & Defense | 🔲 |

Each milestone has a **dedicated walkthrough video** — see the [YouTube Playlist](https://youtube.com/playlist?list=PLhU0J79Smu6kmr6QNJgd0cFa2f-UCwU1K).

---

## Setup & Installation

### 1. Operating System & Dependencies

Developed on **Linux Mint 22 (Cinnamon)**. Ubuntu 22.04+ works identically.

```bash
sudo apt update && sudo apt install -y \
  build-essential gcc g++ cmake git \
  python3 python3-pip python3-venv python3-dev \
  libzmq3-dev libprotobuf-dev protobuf-compiler \
  libxml2-dev libgtk-3-dev libboost-dev libeigen3-dev \
  qtbase5-dev sqlite3 libsqlite3-dev graphviz
```

### 2. Clone and set up Python

```bash
git clone https://github.com/Ksschkw/CongestiQ-FYP..git
cd CongestiQ-FYP.
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install gymnasium stable-baselines3 numpy matplotlib zmq protobuf==3.20.3
```

### 3. Build ns‑3 with the **ns3‑gym** module

```bash
cd ns-3-dev
cd contrib
git clone https://github.com/tkn-tub/ns3-gym.git
cd ns3-gym
git checkout app-ns-3.36+

# Generate protobuf files manually (often needed)
cd model
protoc --cpp_out=. messages.proto
cd ../..

# Patch CMakeLists to include messages.pb.cc and disable broken examples
# (see [m3_as_built.md](docu/m3-single-agent-rl/notes/m3_as_built.md) for the exact edits)

cd ../..
./ns3 configure --enable-examples
./ns3 build

# Install the Python side of ns3‑gym
cd contrib/ns3-gym/model/ns3gym
pip install -e .
# In ns3env.py, change `np.float` → `np.float64` for NumPy 2.x compatibility
```

---

## Usage

### Run a baseline Reno vs CUBIC simulation (M1)

```bash
cd ns-3-dev
./ns3 run scratch/dumbbell-tcp
```

Then generate graphs:

```bash
cd docu/m1-network-sandbox
python3 code/plot_flowmon.py results/dumbbell-tcp-flowmon.xml
```

### Train your own RL agent (M3)

```bash
cd rl_agent
python3 train_m3_v3.py
```

The script starts ns‑3 automatically, trains for 50 k steps, and saves the model.

### Evaluate a trained model

```bash
python3 eval_v3.py
```

Prints throughput, delay, loss and saves a comparison chart.

### Quick bridge test

```bash
cd ns-3-dev/contrib/ns3-gym/examples/rl-tcp
python3 test.py
```

Verifies that ns‑3 ↔ Python communication works.

---

## Key Findings

### M1 – Reno vs CUBIC

- CUBIC grabs more throughput (5331 kbps vs 4611 kbps) but both suffer from **bufferbloat** (~61 ms delay on a 20 ms path).  
- Full observations: [M1 observations](docu/m1-network-sandbox/notes/observations.md)

### M2 – Multi‑flow Dynamics

- BBR gets bullied by aggressive CUBIC flows → 82 ms delay, 2.5% loss.
- The bottleneck queue shows a perfect **TCP sawtooth**, confirming classic AIMD behaviour.
- Jain’s Fairness Index = 0.98 — “fair” but at the cost of high latency.  
- Full observations: [M2 observations](docu/m2-congestion-dynamics/notes/observations.md)

### M3 – Single‑Agent RL

- **Observation bug discovered**: the C++ environment reports a bogus throughput (sum of `bytesInFlight` snapshots, not actual delivery).  
- Because the agent never saw true throughput, all three reward functions failed to push cwnd beyond ~209 kbps.  
- However, the agent learned a **zero‑loss, ultra‑low‑latency policy** (22.8 ms delay, 0% loss) — perfect for real‑time apps, useless for bulk transfer.  
- Lesson: **validate the observation space before designing rewards.**  
- Full experiment log: [M3 experiment log](docu/m3-single-agent-rl/notes/m3_experiments.md)  
- As‑built narrative: [M3 as‑built](docu/m3-single-agent-rl/notes/m3_as_built.md)  
- Observations: [M3 observations](docu/m3-single-agent-rl/notes/observations.md)

---

## Documentation

The `docu/` folder is the project’s memory. Every milestone is self‑contained and linked below.

### M1 – Network Sandbox

- **Code:** [`dumbbell-tcp.cc`](docu/m1-network-sandbox/code/dumbbell-tcp.cc), [`plot_flowmon.py`](docu/m1-network-sandbox/code/plot_flowmon.py)  
- **Results:** [`throughput.png`](docu/m1-network-sandbox/results/throughput.png), [`delay.png`](docu/m1-network-sandbox/results/delay.png), [`loss.png`](docu/m1-network-sandbox/results/loss.png)  
- **Notes:** [`observations.md`](docu/m1-network-sandbox/notes/observations.md), [`video-script.md`](docu/m1-network-sandbox/notes/video-script.md)  
- **Video:** [M1 Walkthrough](https://youtu.be/mEq3XPbP3ms?si=lYSnVfiTKiQXE1Yf)

### M2 – Congestion Dynamics

- **Code:** [`multi-flow-bottleneck.cc`](docu/m2-congestion-dynamics/code/multi-flow-bottleneck.cc), [`plot_multi_flow_stats.py`](docu/m2-congestion-dynamics/code/plot_multi_flow_stats.py), [`plot_queue.py`](docu/m2-congestion-dynamics/code/plot_queue.py)  
- **Results:** [`throughput_m2.png`](docu/m2-congestion-dynamics/results/throughput_m2.png), [`delay_m2.png`](docu/m2-congestion-dynamics/results/delay_m2.png), [`loss_m2.png`](docu/m2-congestion-dynamics/results/loss_m2.png), [`fairness_m2.png`](docu/m2-congestion-dynamics/results/fairness_m2.png), [`queue_occupancy.png`](docu/m2-congestion-dynamics/results/queue_occupancy.png)  
- **Notes:** [`observations.md`](docu/m2-congestion-dynamics/notes/observations.md)  
- **Video:** [M2 Walkthrough](https://youtu.be/rWTC8cTxTPI?si=9-jh4C6XG07urqbG)

### M3 – Single‑Agent RL

- **C++ environment:** [`sim.cc`](docu/m3-single-agent-rl/code/sim.cc), [`tcp-rl-env.h`](docu/m3-single-agent-rl/code/tcp-rl-env.h), [`tcp-rl-env.cc`](docu/m3-single-agent-rl/code/tcp-rl-env.cc)  
- **Reward wrappers:** [`reward_wrapper.py` (v1)](docu/m3-single-agent-rl/code/reward_wrapper.py), [`reward_wrapper_v2.py` (v2)](docu/m3-single-agent-rl/code/reward_wrapper_v2.py), [`reward_wrapper_v3.py` (v3)](docu/m3-single-agent-rl/code/reward_wrapper_v3.py)  
- **Training scripts:** [`train_m3_v2.py`](docu/m3-single-agent-rl/code/train_m3_v2.py), [`train_m3_v3.py`](docu/m3-single-agent-rl/code/train_m3_v3.py)  
- **Evaluation scripts:** [`eval_safe.py`](docu/m3-single-agent-rl/code/eval_safe.py), [`eval_v2.py`](docu/m3-single-agent-rl/code/eval_v2.py), [`eval_v3.py`](docu/m3-single-agent-rl/code/eval_v3.py)  
- **Trained models:** [`ppo_rl_tcp_model.zip` (v1)](docu/m3-single-agent-rl/code/ppo_rl_tcp_model.zip), [`ppo_rl_tcp_model_v2.zip` (v2)](docu/m3-single-agent-rl/code/ppo_rl_tcp_model_v2.zip), [`ppo_rl_tcp_model_v3.zip` (v3)](docu/m3-single-agent-rl/code/ppo_rl_tcp_model_v3.zip)  
- **Results:** [`training_rewards_all.png`](docu/m3-single-agent-rl/results/training_rewards_all.png), [`throughput_comparison_all.png`](docu/m3-single-agent-rl/results/throughput_comparison_all.png), [`delay_comparison_all.png`](docu/m3-single-agent-rl/results/delay_comparison_all.png), [`loss_comparison_all.png`](docu/m3-single-agent-rl/results/loss_comparison_all.png)  
- **Notes:** [`m3_as_built.md`](docu/m3-single-agent-rl/notes/m3_as_built.md), [`m3_experiments.md`](docu/m3-single-agent-rl/notes/m3_experiments.md), [`observations.md`](docu/m3-single-agent-rl/notes/observations.md), [`video-script.md`](docu/m3-single-agent-rl/notes/video-script.md)  
- **Video:** [M3 Walkthrough](https://youtu.be/)

---

## Author

**Kosisochukwu Okafor**  
Final‑Year Student, Software Engineering  
Federal University of Technology, Owerri (FUTO)  

[GitHub](https://github.com/Ksschkw) • [LinkedIn](https://www.linkedin.com/in/okafor-kosisochukwu-65a256384/) • [YouTube Playlist](https://youtube.com/playlist?list=PLhU0J79Smu6kmr6QNJgd0cFa2f-UCwU1K)

---

## Acknowledgements

- ns‑3 and ns3‑gym communities for the simulation tools
- Stable‑Baselines3 and Gymnasium for the RL libraries
- My supervisor for guidance
- Everyone who provided feedback along the way
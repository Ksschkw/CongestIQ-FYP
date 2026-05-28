## 1. Complete Milestone Map: Start to Finish

This is my definitive project scope. Every sub-milestone and micro-milestone from now until defense day. Nothing is left vague, I think.

---

### M1: NETWORK SANDBOX

**Goal:** Build and understand a basic bottleneck topology with two competing TCP flows. Generate metrics, graphs, and animation.

| ID   | Sub-Milestone                     | Micro-Milestones                                                                                                       |
| ---- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| M1.1 | Documentation scaffold            | Create docu folder structure; write M1 README; initialize git tracking                                                 |
| M1.2 | Minimal two-node topology         | Write single-link ns-3 script; compile; run; confirm no errors; log output                                             |
| M1.3 | Dumbbell topology with bottleneck | Two senders, two receivers; 10Mbps/20ms bottleneck; DropTail queue; Reno + CUBIC flows; verify completion              |
| M1.4 | FlowMonitor integration           | Attach FlowMonitor; enable all probes; serialize XML; confirm file exists and is non-empty                             |
| M1.5 | Performance graphs                | Python script to parse FlowMonitor XML; plot throughput over time; plot RTT over time; plot packet loss; save all PNGs |
| M1.6 | NetAnim animation                 | Add AnimationInterface; export XML; open in NetAnim; screenshot congestion moments                                     |
| M1.7 | Observations documentation        | Write observations.md: how Reno vs CUBIC behaved; queue dynamics; fairness observations                                |
| M1.8 | Video walkthrough                 | Record screen; show topology code, run, graphs, NetAnim; upload to YouTube; link in README                             |

---

### M2: CONGESTION DYNAMICS DEEP DIVE

**Goal:** Understand the internal mechanics of congestion—queues, RTT variation, loss events, fairness—across Reno, CUBIC, and BBR.

| ID   | Sub-Milestone                  | Micro-Milestones                                                                                                |
| ---- | ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| M2.1 | Multi-flow topology (4+ flows) | Expand to 4+ senders; mixed TCP variants; longer simulation time                                                |
| M2.2 | Queue occupancy analysis       | Trace queue levels over time; plot queue buildup and drain cycles; identify bufferbloat                         |
| M2.3 | RTT dynamics                   | Measure RTT variation under congestion; plot RTT vs time for each variant; explain sawtooth patterns            |
| M2.4 | Loss event analysis            | Count and timestamp loss events per variant; correlate losses with queue overflow; plot loss distribution       |
| M2.5 | Fairness quantification        | Compute Jain's Fairness Index for each scenario; plot fairness over time; compare Reno vs CUBIC vs BBR fairness |
| M2.6 | BBR behavior analysis          | Run BBR vs CUBIC; observe BBR's model-based pacing; document fairness issues with loss-based flows              |
| M2.7 | Observations documentation     | Write comprehensive notes on congestion dynamics; create reference graphs for later RL comparison               |
| M2.8 | Video walkthrough              | Record deep dive video; explain queue behavior, RTT dynamics, fairness metrics                                  |

---

### M3: SINGLE-AGENT RL ENVIRONMENT

**Goal:** Build the ns3-gym interface, implement one RL-controlled flow against a fixed TCP variant, and verify learning.

| ID   | Sub-Milestone                | Micro-Milestones                                                                                                                                    |
| ---- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| M3.1 | Python RL environment setup  | Create virtual environment; install gymnasium, stable-baselines3, numpy, matplotlib, pandas; verify imports                                         |
| M3.2 | ns3-gym installation         | Clone ns3-gym; build; run example environment; confirm Python-NS3 bridge works                                                                      |
| M3.3 | Custom ns3-gym environment   | Define observation space (cwnd, RTT, delivery rate); define action space (5 discrete actions); define reward function; implement step() and reset() |
| M3.4 | Single-agent training script | Write Python training script; use PPO or DQN; train against fixed CUBIC flow; log rewards to CSV                                                    |
| M3.5 | Convergence analysis         | Plot reward vs episode; identify if/when policy converges; document training duration                                                               |
| M3.6 | Baseline comparison          | Compare RL agent throughput/latency vs CUBIC baseline; plot side-by-side; note improvements/regressions                                             |
| M3.7 | Observations documentation   | Document RL formulation, training challenges, hyperparameter choices, convergence behavior                                                          |
| M3.8 | Video walkthrough            | Record RL environment setup, training run, convergence plot, baseline comparison                                                                    |

---

### M4: MARL TRAINING AND CONVERGENCE

**Goal:** Train multiple agents with CTDE, shared policy, and fairness-aware reward. Demonstrate cooperative behavior.

| ID   | Sub-Milestone                    | Micro-Milestones                                                                                 |
| ---- | -------------------------------- | ------------------------------------------------------------------------------------------------ |
| M4.1 | Multi-agent environment          | Extend ns3-gym env to N agents; shared observation/action spaces; synchronized decision epochs   |
| M4.2 | CTDE architecture implementation | Implement shared policy network; centralized critic (if actor-critic); decentralized actors      |
| M4.3 | Fairness-aware reward            | Add Jain's fairness index term to reward; tune α, β, γ, δ weights; document trade-offs       |
| M4.4 | MARL training run                | Train N agents simultaneously; log per-agent and aggregate rewards; track fairness over episodes |
| M4.5 | Convergence analysis             | Plot multi-agent reward convergence; plot fairness index during training; identify stable policy |
| M4.6 | Policy export                    | Export frozen policy weights; verify deterministic inference; measure inference latency          |
| M4.7 | Observations documentation       | Document CTDE implementation, fairness-reward trade-off, training stability, convergence time    |
| M4.8 | Video walkthrough                | Record MARL training, convergence plots, fairness analysis, exported policy demo                 |

---

### M5: FULL EVALUATION

**Goal:** Rigorously compare the trained MARL policy against Reno, CUBIC, and BBR across multiple metrics and topologies.

| ID   | Sub-Milestone              | Micro-Milestones                                                                                               |
| ---- | -------------------------- | -------------------------------------------------------------------------------------------------------------- |
| M5.1 | Benchmark suite design     | Define evaluation scenarios: 2-flow, 4-flow, mixed variants; define metrics: throughput, RTT, loss, Jain index |
| M5.2 | Throughput comparison      | Run all algorithms on all scenarios; plot bar charts and CDFs; statistical comparison                          |
| M5.3 | Latency comparison         | Compare average and tail RTT; plot RTT distributions; identify worst-case latency per algorithm                |
| M5.4 | Fairness evaluation        | Compute Jain's Fairness Index for each scenario; plot fairness over time; identify any starvation              |
| M5.5 | Packet loss comparison     | Compare loss rates; correlate with throughput; identify whether MARL reduces unnecessary loss                  |
| M5.6 | Robustness testing         | Test with different bottleneck bandwidths, delays, queue sizes; observe policy generalization                  |
| M5.7 | Coexistence testing        | Run MARL alongside legacy flows; test fairness toward non-RL flows                                             |
| M5.8 | Observations documentation | Comprehensive evaluation report with all graphs, tables, and analysis                                          |
| M5.9 | Video walkthrough          | Record full evaluation walkthrough; highlight key findings                                                     |

---

### M6: FINAL DOCUMENTATION AND DEFENSE

**Goal:** Produce the complete academic report, polished codebase, demo video, and defense presentation.

| ID   | Sub-Milestone                         | Micro-Milestones                                                                                   |
| ---- | ------------------------------------- | -------------------------------------------------------------------------------------------------- |
| M6.1 | Chapter 4: Design and Implementation  | Formal write-up of architecture, algorithms, ns-3 environment, RL formulation, training procedure  |
| M6.2 | Chapter 5: Results and Evaluation     | Formal write-up of all evaluation results, graphs, tables, statistical analysis                    |
| M6.3 | Chapter 6: Conclusion and Future Work | Summary, contributions, limitations, future directions                                             |
| M6.4 | Code repository cleanup               | Remove dead code; add comprehensive README; license file; requirements.txt; ensure reproducibility |
| M6.5 | Final demo video                      | Polished 10-15 minute demonstration covering problem, approach, results, live simulation           |
| M6.6 | Defense presentation                  | PowerPoint/Google Slides; key diagrams; results summary; prepared Q&A responses                    |
| M6.7 | Print and bind                        | Final formatting; table of contents; list of figures; references; submission-ready PDF             |
| M6.8 | Repository public release             | Make GitHub public; upload video; share on LinkedIn                                                |

---

### Milestone Dependency Graph

```
M1 (Network Sandbox)
  ↓
M2 (Congestion Dynamics)
  ↓
M3 (Single-Agent RL) ──→ M4 (MARL Training)
                              ↓
                           M5 (Evaluation)
                              ↓
                           M6 (Documentation & Defense)
```

M1 and M2 must be sequential. M3 and M4 build on M2's understanding. M5 depends on M4 producing a trained policy. M6 depends on everything.

---

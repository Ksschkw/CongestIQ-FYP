## First Documentation File

```
FYP/
├── docu/                          # All project documentation
│   ├── README.md                  # This file
│   ├── m1-network-sandbox/        # Milestone 1
│   ├── m2-congestion-dynamics/    # Milestone 2
│   ├── m3-single-agent-rl/        # Milestone 3
│   ├── m4-marl-training/          # Milestone 4
│   ├── m5-evaluation/             # Milestone 5
│   ├── m6-final-documentation/    # Milestone 6
│   └── _global-notes/             # Cross-cutting notes
├── ns-3-dev/                      # ns-3 simulator (gitignored)
├── netanim/                       # NetAnim visualizer (gitignored)
├── src/                           # Custom ns-3 modules (future)
├── rl-agent/                      # Python RL code (future)
├── .gitignore
└── README.md                      # Project-level README
```

## Milestone Map

| ID | Milestone                       | Status      | Completion Date |
| -- | ------------------------------- | ----------- | --------------- |
| M1 | Network Sandbox                 | Finished    | 26th May 2026   |
| M2 | Congestion Dynamics             | Finished    | 20 June 2026    |
| M3 | Single-Agent RL Environment     | Finished    | 9 August 2026   |
| M4 | MARL Training and Convergence   | Finished    | 15 August 2026  |
| M5 | Full Evaluation                 | Finished    | 3 September 2026 |
| M6 | Final Documentation and Defense | In progress | n/a             |

## Correctness Repair (October 2026)

During defence preparation I rechecked the multi-agent evaluation and found that
the reported MARL numbers were produced by the ns-3 default TCP CUBIC, not by the
trained policy. The evaluation was invalid.

The cause and the repair are documented in:

- `m4-marl-training/notes/m4_root_cause_correction.md`
- `m4-marl-training/notes/m4_control_verification.md`
- `m4-marl-training/notes/m4_retrain_v2.md`
- `m5-evaluation/notes/m5_corrected_evaluation.md`

The corrected code is mirrored into `m4-marl-training/code/m4.3-marl-two-agents/`
and `m5-evaluation/code/`. Live files are copied into those folders with
`docu/sync_code.sh`.

## Environment

- **OS:** Linux
- **Simulator:** ns-3 (latest dev)
- **Visualization:** NetAnim
- **RL Framework:** Python + gymnasium + stable-baselines3 (planned)
- **Graphing:** matplotlib, pandas

## Key Design Decisions

1. **Simulation-based offline training:** RL agents train in ns-3, not on live networks
2. **ns3-gym interface:** Python RL agent communicates with ns-3 via ns3-gym
3. **CTDE paradigm:** Centralized Training, Decentralized Execution for MARL
4. **Synchronized decision epochs:** Agents act once per RTT, not per ACK
5. **Discrete percentage actions:** maintain, ±10%, ±20% cwnd adjustments
6. **Multi-objective reward:** throughput, minus delay, minus loss, plus fairness

## Videos

All milestone walkthroughs are uploaded to YouTube:

- [Playlist link to be added]

## References

See the formal seminar report for the full reference list.
Key foundational references: Jacobson (1988), Ha et al. (2008), Kurose & Ross (2021), RFC 9743, BBR Internet Draft.

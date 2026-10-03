#!/usr/bin/env python3
"""
verify_control.py

Purpose: prove that the trained/queried RL actions really own the TCP
congestion window in the multi-agent environment.

It runs the fixed ns-3 program several times on the same topology, each time
with a different *constant* action policy, and records the raw observation
vector (cwnd, smoothed RTT, loss placeholder, throughput, for two agents).

If the RL env owns cwnd, the constant policies must produce clearly different
cwnd and throughput traces. If ns-3's own congestion control still owns cwnd
(the old bug), all policies produce the same CUBIC-like trace.

Run with the project venv:
    /home/ksschkw/Projects/fyp/venv/bin/python rl_agent/verify_control.py
"""

import os
import csv
import sys
import argparse
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = "/home/ksschkw/Projects/fyp"
SIM_DIR = os.path.join(REPO, "ns-3-dev/contrib/ns3-gym/examples/marl-multi-tcp")
OUT_DIR = os.path.join(REPO, "docu/m5-evaluation/results/control_verification")

# action id -> (label, multiplier) matching marl-multi-env.cc.
# Action 0 is "hold", which is the safe starting point for the SB3 policy.
POLICIES = {
    "increase20": (3, 1.2),
    "increase10": (1, 1.1),
    "hold": (0, 1.0),
    "decrease10": (2, 0.9),
    "decrease20": (4, 0.8),
}


def run_policy(name, action_id, duration, seed, debug):
    from ns3gym import ns3env

    os.chdir(SIM_DIR)
    env = ns3env.Ns3Env(
        port=0,                      # pick a free port, pass it to the sim
        stepTime=0.1,
        startSim=True,
        simSeed=seed,
        simArgs={"--duration": duration, "--flowmon": 0},
        debug=debug,
    )

    rows = []
    step = 0
    obs = env.get_state()[0]
    # Joint discrete action for two agents: agent 0 is the least significant
    # digit, so the same action for both agents is action_id + 5 * action_id.
    joint_action = action_id + 5 * action_id
    while True:
        env.step(joint_action)
        obs, reward, done, _ = env.get_state()
        obs = np.asarray(obs, dtype=np.float64).flatten()
        if obs.size >= 8:
            rows.append([step, obs[0], obs[3], obs[4], obs[7], float(reward)])
        step += 1
        if done:
            break
    env.close()

    out_csv = os.path.join(OUT_DIR, "control_%s.csv" % name)
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "cwnd0_bytes", "thr0_bps", "cwnd1_bytes", "thr1_bps", "reward"])
        w.writerows(rows)

    arr = np.array(rows, dtype=np.float64)
    summary = {
        "policy": name,
        "action_id": action_id,
        "steps": len(rows),
        "mean_cwnd0": float(arr[:, 1].mean()),
        "mean_thr0_kbps": float(arr[:, 2].mean() / 1000.0),
        "mean_thr_sum_kbps": float((arr[:, 2] + arr[:, 4]).mean() / 1000.0),
        "final_cwnd0": float(arr[-1, 1]),
    }
    print("[verify_control] %-11s mean cwnd0=%9.0f B  mean total thr=%8.1f kbps"
          % (name, summary["mean_cwnd0"], summary["mean_thr_sum_kbps"]))
    return arr, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    traces = {}
    summaries = []
    for name, (action_id, _mult) in POLICIES.items():
        arr, summary = run_policy(name, action_id, args.duration, args.seed, args.debug)
        traces[name] = arr
        summaries.append(summary)

    with open(os.path.join(OUT_DIR, "control_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        w.writeheader()
        w.writerows(summaries)

    # Plot cwnd and throughput per policy.
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for name, arr in traces.items():
        axes[0].plot(arr[:, 0] * 0.1, arr[:, 1] / 1024.0, label=name)
        axes[1].plot(arr[:, 0] * 0.1, (arr[:, 2] + arr[:, 4]) / 1000.0, label=name)
    axes[0].set_ylabel("agent 0 cwnd (KiB)")
    axes[1].set_ylabel("total throughput (kbps)")
    axes[1].set_xlabel("simulation time (s)")
    axes[0].set_title("Constant-action control test: RL actions own cwnd")
    for ax in axes:
        ax.grid(True, alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "control_verification.png"), dpi=130)
    plt.close(fig)
    print("[verify_control] wrote", OUT_DIR)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
m5_evaluate.py

Full M5 evaluation for the corrected multi-agent RL policy.

It can run the three TCP baselines, run the trained MARL policy for several
seeds, parse every FlowMonitor XML with the same code path, and write a
comparison table plus plots.

Examples
--------
Run only the baselines:
    venv/bin/python rl_agent/m5_evaluate.py --baselines

Evaluate the trained model for three seeds (run after training has stopped):
    venv/bin/python rl_agent/m5_evaluate.py --marl --seeds 1 2 3

Rebuild the plots from already-saved flowmon files:
    venv/bin/python rl_agent/m5_evaluate.py --plot-only --marl
"""

import os
import csv
import json
import glob
import shutil
import argparse
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = "/home/ksschkw/Projects/fyp"
NS3_DIR = os.path.join(REPO, "ns-3-dev")
SIM_DIR = os.path.join(NS3_DIR, "contrib/ns3-gym/examples/marl-multi-tcp")
RESULT_DIR = os.path.join(REPO, "docu/m5-evaluation/results")
MODEL = os.path.join(SIM_DIR, "ppo_marl_multi_v2.zip")

BASELINES = {
    "Reno": "TcpNewReno",
    "CUBIC": "TcpCubic",
    "BBR": "TcpBbr",
}


def parse_flowmon(path):
    """Return per-flow metric dicts from an ns-3 FlowMonitor XML.

    FlowMonitor records both directions of each TCP connection: the
    sender-to-receiver data flow and the receiver-to-sender acknowledgment
    flow. Only the data flows matter here, so the Ipv4FlowClassifier is used
    to keep flows whose destination port is the sink port (50000 or 50001).
    """
    tree = ET.parse(path)
    root = tree.getroot()

    # Destination port per flowId, when the classifier is present.
    dest_port = {}
    for fe in root.findall(".//Ipv4FlowClassifier/Flow"):
        dest_port[fe.get("flowId")] = fe.get("destinationPort")

    data_ports = {"50000", "50001"}
    flows = []
    for fe in root.findall("./FlowStats/Flow"):
        txb = fe.get("txBytes")
        if txb is None:
            continue
        fid = fe.get("flowId")
        if dest_port and dest_port.get(fid) is not None and dest_port.get(fid) not in data_ports:
            continue  # this is an acknowledgment flow
        txb = int(txb)
        rxb = int(fe.get("rxBytes") or 0)
        txp = int(fe.get("txPackets") or 0)
        lost = int(fe.get("lostPackets") or 0)

        def ns_attr(name):
            v = fe.get(name)
            if v is None:
                return 0.0
            return float(v.replace("+", "").replace("ns", ""))

        t0 = ns_attr("timeFirstTxPacket")
        t1 = ns_attr("timeLastRxPacket")
        dur = max(t1 - t0, 1.0) / 1e9
        rxp = max(txp - lost, 0)
        throughput_kbps = (rxb * 8) / dur / 1000.0
        delay_ms = (ns_attr("delaySum") / (rxp * 1e6)) if rxp > 0 else 0.0
        loss_ratio = (lost / txp) if txp > 0 else 0.0
        flows.append({
            "flowId": fid,
            "txBytes": txb,
            "rxBytes": rxb,
            "throughput_kbps": throughput_kbps,
            "mean_delay_ms": delay_ms,
            "loss_ratio": loss_ratio,
        })
    flows.sort(key=lambda f: f["txBytes"], reverse=True)
    return flows


def jain(values):
    values = np.asarray([v for v in values if v > 0], dtype=np.float64)
    if values.size == 0:
        return 0.0
    return float((values.sum() ** 2) / (values.size * (values ** 2).sum()))


def summarise(label, flows):
    """Reduce a list of per-flow dicts to one scenario-level row."""
    n = len(flows)
    thr = [f["throughput_kbps"] for f in flows]
    row = {
        "scenario": label,
        "n_flows": n,
        "total_throughput_kbps": float(np.sum(thr)),
        "utilisation_pct": float(np.sum(thr) / 10000.0 * 100.0),  # 10 Mbps = 10000 kbps
        "mean_delay_ms": float(np.mean([f["mean_delay_ms"] for f in flows])) if n else 0.0,
        "loss_pct": float(np.mean([f["loss_ratio"] for f in flows]) * 100.0) if n else 0.0,
        "jain_fairness": jain(thr),
        "per_flow_throughput_kbps": [round(t, 1) for t in thr],
    }
    return row


def run_baselines(duration):
    rows = []
    for label, variant in BASELINES.items():
        print("[m5_evaluate] running baseline", label, "(%s)" % variant)
        cmd = './ns3 run "two-flow-baseline --tcp=%s --duration=%s"' % (variant, duration)
        subprocess.run(cmd, shell=True, cwd=NS3_DIR, check=True)
        src = os.path.join(NS3_DIR, "two-flow-%s.flowmon" % variant)
        dst = os.path.join(RESULT_DIR, "baseline_%s.flowmon" % label)
        shutil.copyfile(src, dst)
        rows.append(summarise(label, parse_flowmon(dst)))
    return rows


def run_marl(seeds, duration, model_path):
    """Run the trained model. Imports SB3 lazily so --plot-only needs no model."""
    from stable_baselines3 import PPO
    import sys
    sys.path.insert(0, os.path.join(REPO, "rl_agent"))
    from marl_multi_env import MarlMultiEnv

    os.chdir(SIM_DIR)
    rows = []
    for seed in seeds:
        print("[m5_evaluate] evaluating MARL seed", seed)
        env = MarlMultiEnv(port=5555, stepTime=0.1, startSim=True, simSeed=seed,
                           debug=False, simArgs={"--duration": duration})
        model = PPO.load(model_path)
        obs, _ = env.reset()
        total_reward = 0.0
        done = False
        cwnd_trace = []  # [step, cwnd_agent0_bytes, cwnd_agent1_bytes]
        step = 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            total_reward += float(reward)
            raw = env.last_raw_obs
            cwnd_trace.append([step, float(raw[0]), float(raw[4])])
            step += 1
        env.close()

        trace_path = os.path.join(RESULT_DIR, "marl_v2_seed%d_cwnd.csv" % seed)
        with open(trace_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["step", "cwnd_agent0_bytes", "cwnd_agent1_bytes"])
            w.writerows(cwnd_trace)

        src = os.path.join(NS3_DIR, "marl-multi-flowmon.xml")
        dst = os.path.join(RESULT_DIR, "marl_v2_seed%d.flowmon" % seed)
        shutil.copyfile(src, dst)
        row = summarise("MARL (seed %d)" % seed, parse_flowmon(dst))
        row["episode_reward"] = round(total_reward, 1)
        rows.append(row)
    return rows


def baseline_rows_from_disk():
    rows = []
    for label in BASELINES:
        path = os.path.join(RESULT_DIR, "baseline_%s.flowmon" % label)
        if os.path.exists(path):
            rows.append(summarise(label, parse_flowmon(path)))
    return rows


def marl_rows_from_disk():
    rows = []
    for path in sorted(glob.glob(os.path.join(RESULT_DIR, "marl_v2_seed*.flowmon"))):
        seed = os.path.basename(path).replace("marl_v2_seed", "").replace(".flowmon", "")
        rows.append(summarise("MARL (seed %s)" % seed, parse_flowmon(path)))
    return rows


def aggregate_marl(rows):
    if not rows:
        return None
    keys = ["total_throughput_kbps", "mean_delay_ms", "loss_pct", "jain_fairness",
            "utilisation_pct"]
    agg = {"scenario": "MARL (mean of %d seeds)" % len(rows), "n_flows": 2}
    for k in keys:
        vals = [r[k] for r in rows]
        agg[k] = float(np.mean(vals))
        agg[k + "_std"] = float(np.std(vals))
    agg["per_flow_throughput_kbps"] = rows[0]["per_flow_throughput_kbps"]
    return agg


def write_table(rows, path):
    if not rows:
        return
    fields = ["scenario", "n_flows", "total_throughput_kbps", "utilisation_pct",
              "mean_delay_ms", "loss_pct", "jain_fairness", "per_flow_throughput_kbps"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("[m5_evaluate] wrote", path)


def plot_comparison(rows, out_dir):
    if not rows:
        return
    labels = [r["scenario"].replace(" (", "\n(") for r in rows]
    panels = [
        ("total_throughput_kbps", "Total throughput (kbps)", None),
        ("mean_delay_ms", "Mean delay (ms)", None),
        ("loss_pct", "Mean loss (%)", None),
        ("jain_fairness", "Jain fairness index", (0.9, 1.005)),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (key, title, ylim) in zip(axes.ravel(), panels):
        vals = [r[key] for r in rows]
        colors = ["tab:green" if r["scenario"].startswith("MARL") else "tab:blue"
                  for r in rows]
        ax.bar(range(len(rows)), vals, color=colors)
        ax.set_title(title)
        ax.set_xticks(range(len(rows)))
        ax.set_xticklabels(labels, fontsize=8)
        if ylim:
            ax.set_ylim(*ylim)
        ax.grid(True, axis="y", alpha=0.3)
    fig.suptitle("M5 two-flow comparison (10 Mbps, 20 ms, DropTail 100 packets, 60 s)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "m5_corrected_comparison.png"), dpi=130)
    plt.close(fig)
    print("[m5_evaluate] wrote m5_corrected_comparison.png")


def plot_cwnd_traces(out_dir):
    """Plot the congestion window that the policy produced for each seed."""
    files = sorted(glob.glob(os.path.join(out_dir, "marl_v2_seed*_cwnd.csv")))
    if not files:
        return
    fig, ax = plt.subplots(figsize=(11, 5))
    for path in files:
        seed = os.path.basename(path).replace("marl_v2_seed", "").replace("_cwnd.csv", "")
        data = np.genfromtxt(path, delimiter=",", names=True)
        ax.plot(data["step"] * 0.1, data["cwnd_agent0_bytes"] / 1024.0,
                label="seed %s agent 0" % seed)
        ax.plot(data["step"] * 0.1, data["cwnd_agent1_bytes"] / 1024.0,
                label="seed %s agent 1" % seed, linestyle="--")
    ax.set_xlabel("simulation time (s)")
    ax.set_ylabel("congestion window (KiB)")
    ax.set_title("Congestion window under the trained multi-agent policy")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "marl_v2_cwnd_traces.png"), dpi=130)
    plt.close(fig)
    print("[m5_evaluate] wrote marl_v2_cwnd_traces.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baselines", action="store_true")
    ap.add_argument("--marl", action="store_true")
    ap.add_argument("--plot-only", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2, 3])
    ap.add_argument("--duration", type=float, default=60.0)
    ap.add_argument("--model", default=MODEL,
                    help="Path to the PPO model to evaluate")
    args = ap.parse_args()

    os.makedirs(RESULT_DIR, exist_ok=True)

    rows = []
    if not args.plot_only and args.baselines:
        rows += run_baselines(args.duration)
    else:
        rows += baseline_rows_from_disk()

    marl_rows = []
    if not args.plot_only and args.marl:
        marl_rows = run_marl(args.seeds, args.duration, args.model)
    elif args.marl or args.plot_only:
        marl_rows = marl_rows_from_disk()

    rows += marl_rows
    agg = aggregate_marl(marl_rows)
    if agg:
        rows.append(agg)

    write_table(rows, os.path.join(RESULT_DIR, "m5_corrected_summary.csv"))
    with open(os.path.join(RESULT_DIR, "m5_corrected_summary.json"), "w") as f:
        json.dump(rows, f, indent=2)
    plot_comparison(rows, RESULT_DIR)
    plot_cwnd_traces(RESULT_DIR)

    print("\n%-28s %10s %8s %8s %8s" % ("scenario", "thr(kbps)", "delay", "loss%", "jain"))
    for r in rows:
        print("%-28s %10.1f %8.2f %8.3f %8.4f"
              % (r["scenario"], r["total_throughput_kbps"], r["mean_delay_ms"],
                 r["loss_pct"], r["jain_fairness"]))


if __name__ == "__main__":
    main()

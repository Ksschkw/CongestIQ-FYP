"""Parse baseline flowmon files and plot M5 comparison charts."""
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import numpy as np
import os

def parse_flowmon(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    flows = []
    for fe in root.findall('.//Flow'):
        txb = fe.get('txBytes')
        if txb is None: continue
        txb = int(txb)
        rxb = int(fe.get('rxBytes') or 0)
        txp = int(fe.get('txPackets') or 0)
        lost = int(fe.get('lostPackets') or 0)
        t0 = float(fe.get('timeFirstTxPacket').replace('+','').replace('ns',''))
        t1 = float(fe.get('timeLastRxPacket').replace('+','').replace('ns',''))
        dur = max(t1 - t0, 1e-9) / 1e9
        rxp = txp - lost
        thr = (rxb * 8) / dur / 1000.0
        dsum = float(fe.get('delaySum').replace('+','').replace('ns',''))
        delay = dsum / (rxp * 1e6) if rxp > 0 else 0.0
        loss_ratio = lost / txp if txp > 0 else 0.0
        flows.append({'txBytes': txb, 'throughput_kbps': thr, 'mean_delay_ms': delay, 'loss_ratio': loss_ratio})
    flows.sort(key=lambda x: x['txBytes'], reverse=True)
    return flows

def fairness(thr_list):
    if len(thr_list) < 2: return 0.0
    sum_t = sum(thr_list)
    sum_sq = sum(t*t for t in thr_list)
    if sum_sq == 0: return 0.0
    return (sum_t ** 2) / (len(thr_list) * sum_sq)

def main():
    base_dir = "/home/ksschkw/Projects/fyp/ns-3-dev"
    variants = ["TcpNewReno", "TcpCubic", "TcpBbr"]
    data = {}

    for var in variants:
        path = os.path.join(base_dir, f"two-flow-{var}.flowmon")
        if not os.path.exists(path):
            print(f"Missing {path}")
            continue
        flows = parse_flowmon(path)
        if len(flows) >= 2:
            thr = [flows[0]['throughput_kbps'], flows[1]['throughput_kbps']]
            delay = [flows[0]['mean_delay_ms'], flows[1]['mean_delay_ms']]
            loss = [flows[0]['loss_ratio']*100, flows[1]['loss_ratio']*100]
            data[var] = {
                'throughput': thr,
                'delay': delay,
                'loss': loss,
                'fairness': fairness(thr)
            }
            print(f"{var}: throughput={thr}, delay={delay}, loss={loss}, fairness={fairness(thr):.4f}")
        else:
            print(f"{var}: not enough flows")

    # MARL data
    marl_throughput = [5112.1, 4824.8]
    marl_delay = [60.96, 60.80]
    marl_loss = [0.04, 0.05]
    marl_fairness = 0.9992

    out_dir = "/home/ksschkw/Projects/fyp/docu/m5-evaluation/results"
    os.makedirs(out_dir, exist_ok=True)

    # Per-flow throughput chart
    labels = ['MARL Ag1', 'MARL Ag2', 'Reno1', 'Reno2', 'CUBIC1', 'CUBIC2', 'BBR1', 'BBR2']
    throughputs = marl_throughput + data.get('TcpNewReno', {}).get('throughput', [0,0]) + data.get('TcpCubic', {}).get('throughput', [0,0]) + data.get('TcpBbr', {}).get('throughput', [0,0])
    plt.figure(figsize=(10,5))
    bars = plt.bar(labels, throughputs, color=['green','lime','red','salmon','orange','gold','blue','lightblue'])
    plt.ylabel('Throughput (kbps)')
    plt.title('M5: Per-Flow Throughput Comparison')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'm5_throughput_comparison.png'))
    plt.close()

    # Fairness chart
    fairness_values = [marl_fairness] + [data.get(v, {}).get('fairness', 0) for v in variants]
    labels_fair = ['MARL', 'Reno', 'CUBIC', 'BBR']
    plt.figure(figsize=(6,4))
    plt.bar(labels_fair, fairness_values, color=['green','red','orange','blue'])
    plt.ylabel("Jain's Fairness Index")
    plt.title('M5: Fairness Comparison')
    plt.ylim(0,1.1)
    for i, v in enumerate(fairness_values):
        plt.text(i, v+0.02, f'{v:.3f}', ha='center')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'm5_fairness_comparison.png'))
    plt.close()

    # Delay chart (average per variant)
    avg_delays = [np.mean(marl_delay)] + [np.mean(data.get(v, {}).get('delay', [0,0])) for v in variants]
    plt.figure(figsize=(6,4))
    plt.bar(labels_fair, avg_delays, color=['green','red','orange','blue'])
    plt.ylabel('Average Delay (ms)')
    plt.title('M5: Average Delay Comparison')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'm5_delay_comparison.png'))
    plt.close()

    # Loss chart (average per variant)
    avg_loss = [np.mean(marl_loss)] + [np.mean(data.get(v, {}).get('loss', [0,0])) for v in variants]
    plt.figure(figsize=(6,4))
    plt.bar(labels_fair, avg_loss, color=['green','red','orange','blue'])
    plt.ylabel('Average Loss (%)')
    plt.title('M5: Average Packet Loss Comparison')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'm5_loss_comparison.png'))
    plt.close()

    print("Charts saved to", out_dir)

if __name__ == "__main__":
    main()
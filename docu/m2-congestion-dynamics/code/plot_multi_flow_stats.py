#!/usr/bin/env python3
"""
plot_multi_flow_stats.py
Parse M2 FlowMonitor XML (4 flows) and generate:
  - Throughput bar chart
  - Delay bar chart
  - Loss bar chart
  - Fairness index (Jain) printed and plotted
"""

import sys
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

def parse_ns_time(tstr):
    return float(tstr.replace('+','').replace('ns',''))

def get_flows(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    # Identify forward data flows (destination port 9)
    data_ids = set()
    classifier = root.find('Ipv4FlowClassifier')
    if classifier is not None:
        for flow in classifier.findall('Flow'):
            if flow.get('protocol') == '6' and flow.get('destinationPort') == '9':
                data_ids.add(int(flow.get('flowId')))
    flows = []
    stats = root.find('FlowStats')
    if stats is not None:
        for fe in stats.findall('Flow'):
            fid = int(fe.get('flowId'))
            if fid not in data_ids: continue
            tx_bytes = int(fe.get('txBytes'))
            rx_bytes = int(fe.get('rxBytes'))
            tx_pkts = int(fe.get('txPackets'))
            lost_pkts = int(fe.get('lostPackets'))
            t0 = parse_ns_time(fe.get('timeFirstTxPacket'))
            t1 = parse_ns_time(fe.get('timeLastRxPacket'))
            dur_ns = t1 - t0
            if dur_ns <= 0: dur_ns = 1e-9
            dur_s = dur_ns / 1e9
            rx_pkts = tx_pkts - lost_pkts
            throughput_kbps = (rx_bytes * 8) / dur_s / 1000.0
            delay_sum = parse_ns_time(fe.get('delaySum'))
            mean_delay_ms = (delay_sum / (rx_pkts * 1e6)) if rx_pkts > 0 else 0.0
            loss_ratio = lost_pkts / tx_pkts if tx_pkts > 0 else 0.0
            flows.append({
                'flowId': fid,
                'throughput_kbps': throughput_kbps,
                'mean_delay_ms': mean_delay_ms,
                'loss_ratio': loss_ratio,
                'rx_bytes': rx_bytes
            })
    return flows

def jain_fairness(throughputs):
    # Jain's index = (sum x_i)^2 / (n * sum(x_i^2))
    n = len(throughputs)
    if n == 0: return 0.0
    sum_t = sum(throughputs)
    sum_sq = sum(t**2 for t in throughputs)
    if sum_sq == 0: return 0.0
    return (sum_t ** 2) / (n * sum_sq)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 plot_multi_flow_stats.py <flowmon.xml>")
        sys.exit(1)
    xml_file = sys.argv[1]
    flows = get_flows(xml_file)
    if not flows:
        print("No data flows found.")
        sys.exit(1)

    # Sort by flowId for consistency
    flows.sort(key=lambda x: x['flowId'])
    fids = [str(f['flowId']) for f in flows]
    throughputs = [f['throughput_kbps'] for f in flows]
    delays = [f['mean_delay_ms'] for f in flows]
    losses = [f['loss_ratio']*100 for f in flows]

    # Print stats
    print("Per-flow statistics:")
    for f in flows:
        print(f"  Flow {f['flowId']}: Throughput={f['throughput_kbps']:.1f} kbps, "
              f"Delay={f['mean_delay_ms']:.2f} ms, Loss={f['loss_ratio']*100:.2f}%")

    fairness = jain_fairness(throughputs)
    print(f"\nJain's Fairness Index: {fairness:.4f}")

    import os
    out_dir = os.path.dirname(xml_file) or '.'
    
    # Throughput
    plt.figure(figsize=(10,5))
    bars = plt.bar(fids, throughputs, color=['#2196F3','#FF9800','#4CAF50','#9C27B0'])
    plt.xlabel('Flow ID')
    plt.ylabel('Throughput (kbps)')
    plt.title('Per-Flow Throughput')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    for bar, val in zip(bars, throughputs):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height()+5, f'{val:.1f}',
                 ha='center', va='bottom', fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'throughput_m2.png'), dpi=150)
    plt.close()

    # Delay
    plt.figure(figsize=(10,5))
    plt.bar(fids, delays, color=['#2196F3','#FF9800','#4CAF50','#9C27B0'])
    plt.xlabel('Flow ID')
    plt.ylabel('Mean Delay (ms)')
    plt.title('Per-Flow Mean Delay')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    for i, val in enumerate(delays):
        plt.text(i, val+0.5, f'{val:.2f}', ha='center', fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'delay_m2.png'), dpi=150)
    plt.close()

    # Loss
    plt.figure(figsize=(10,5))
    plt.bar(fids, losses, color=['#2196F3','#FF9800','#4CAF50','#9C27B0'])
    plt.xlabel('Flow ID')
    plt.ylabel('Loss Ratio (%)')
    plt.title('Per-Flow Packet Loss Ratio')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    for i, val in enumerate(losses):
        plt.text(i, val+0.01, f'{val:.2f}%', ha='center', fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'loss_m2.png'), dpi=150)
    plt.close()

    # Fairness as a simple number on a plot (optional)
    plt.figure(figsize=(4,3))
    plt.text(0.5, 0.5, f"Jain's Fairness Index = {fairness:.4f}", 
             ha='center', va='center', fontsize=18, transform=plt.gca().transAxes)
    plt.axis('off')
    plt.savefig(os.path.join(out_dir, 'fairness_m2.png'), dpi=150)
    plt.close()
    print("Plots saved.")

if __name__ == "__main__":
    main()
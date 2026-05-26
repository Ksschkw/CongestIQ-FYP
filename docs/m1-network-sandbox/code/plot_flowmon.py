#!/usr/bin/env python3
"""
plot_flowmon.py
Milestone M1.5: Parse FlowMonitor XML and generate performance graphs.

FIXED VERSION: Reads FlowMonitor XML where flow stats are attributes of <Flow>
elements, not child elements. Filters only the forward TCP data flows
(destination port 9, protocol 6) using the Ipv4FlowClassifier section.

WHAT THIS SCRIPT DOES:
    1. Reads the FlowMonitor XML file exported by ns-3
    2. Identifies the forward TCP data flows (excludes reverse ACK flows)
    3. Extracts per-flow statistics: throughput, mean delay, packet loss ratio
    4. Plots bar charts for throughput, delay, and loss
    5. Saves plots as PNG files in the same directory as the XML

USAGE:
    python3 plot_flowmon.py path/to/dumbbell-tcp-flowmon.xml
"""

import sys
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving files

def parse_ns_time(time_str):
    """
    Convert ns-3 time string (e.g., '+2.20557e+07ns') to nanoseconds as float.
    """
    return float(time_str.replace('+', '').replace('ns', ''))

def parse_flowmon_xml(xml_file):
    """
    Parse the ns-3 FlowMonitor XML and extract per-flow stats for forward TCP data flows.
    
    The XML has two sections:
    1. <FlowStats> with <Flow> elements containing attributes like txBytes, delaySum, etc.
    2. <Ipv4FlowClassifier> which maps flowId to source/destination IP and port.
    
    We use the classifier to find flows where destinationPort="9" and protocol="6",
    which correspond to the BulkSend TCP data flows. The reverse ACK flows (source port 9)
    are ignored.
    
    Returns:
        list of dicts with keys: flowId, throughput_kbps, mean_delay_ms, loss_ratio
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Step 1: Identify forward data flow IDs from the Ipv4FlowClassifier
    data_flow_ids = set()
    classifier = root.find('Ipv4FlowClassifier')
    if classifier is not None:
        for flow in classifier.findall('Flow'):
            if flow.get('protocol') == '6' and flow.get('destinationPort') == '9':
                data_flow_ids.add(int(flow.get('flowId')))
    
    # Step 2: Extract stats from FlowStats section for those flow IDs
    flows = []
    flow_stats = root.find('FlowStats')
    if flow_stats is None:
        print("No FlowStats element found.")
        return flows
    
    for flow_elem in flow_stats.findall('Flow'):
        fid = int(flow_elem.get('flowId'))
        if fid not in data_flow_ids:
            continue   # skip reverse ACK flows
        
        # Read attributes (all are present in your XML)
        tx_bytes = int(flow_elem.get('txBytes'))
        rx_bytes = int(flow_elem.get('rxBytes'))
        tx_packets = int(flow_elem.get('txPackets'))
        lost_packets = int(flow_elem.get('lostPackets'))
        
        time_first_ns = parse_ns_time(flow_elem.get('timeFirstTxPacket'))
        time_last_ns = parse_ns_time(flow_elem.get('timeLastRxPacket'))
        delay_sum_ns = parse_ns_time(flow_elem.get('delaySum'))
        
        # Duration in seconds (avoid division by zero)
        duration_ns = time_last_ns - time_first_ns
        if duration_ns <= 0:
            duration_ns = 1e-9   # effectively zero seconds
        duration_s = duration_ns / 1e9
        
        # Received packets (approximately tx_packets - lost_packets)
        rx_packets = tx_packets - lost_packets
        
        # Throughput in kbps: (rx_bytes * 8 bits) / duration_s / 1000
        throughput_kbps = (rx_bytes * 8) / duration_s / 1000.0
        
        # Mean delay in ms: delaySum is in ns, divide by rx_packets, convert to ms
        mean_delay_ms = (delay_sum_ns / (rx_packets * 1e6)) if rx_packets > 0 else 0.0
        
        # Packet loss ratio
        loss_ratio = lost_packets / tx_packets if tx_packets > 0 else 0.0
        
        flow_data = {
            'flowId': fid,
            'throughput_kbps': throughput_kbps,
            'mean_delay_ms': mean_delay_ms,
            'loss_ratio': loss_ratio,
        }
        flows.append(flow_data)
    
    return flows

def plot_throughput(flows, output_file):
    """Bar chart of throughput per flow."""
    flow_ids = [str(f['flowId']) for f in flows]
    throughputs = [f['throughput_kbps'] for f in flows]
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(flow_ids, throughputs, color=['#2196F3', '#FF9800'])
    plt.xlabel('Flow ID')
    plt.ylabel('Throughput (kbps)')
    plt.title('Per-Flow Throughput')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for bar, val in zip(bars, throughputs):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                 f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"Throughput plot saved to: {output_file}")

def plot_delay(flows, output_file):
    """Bar chart of mean delay per flow."""
    flow_ids = [str(f['flowId']) for f in flows]
    delays = [f['mean_delay_ms'] for f in flows]
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(flow_ids, delays, color=['#4CAF50', '#F44336'])
    plt.xlabel('Flow ID')
    plt.ylabel('Mean Delay (ms)')
    plt.title('Per-Flow Mean Delay')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for bar, val in zip(bars, delays):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f'{val:.2f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"Delay plot saved to: {output_file}")

def plot_loss(flows, output_file):
    """Bar chart of packet loss ratio per flow."""
    flow_ids = [str(f['flowId']) for f in flows]
    losses = [f['loss_ratio'] * 100 for f in flows]  # percentage
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(flow_ids, losses, color=['#9C27B0', '#00BCD4'])
    plt.xlabel('Flow ID')
    plt.ylabel('Packet Loss Ratio (%)')
    plt.title('Per-Flow Packet Loss Ratio')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for bar, val in zip(bars, losses):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 f'{val:.2f}%', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"Loss plot saved to: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 plot_flowmon.py <flowmon-xml-file>")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    print(f"Parsing {xml_file}...")
    flows = parse_flowmon_xml(xml_file)
    
    if not flows:
        print("No data flows found in XML. Check the file and Ipv4FlowClassifier section.")
        sys.exit(1)
    
    print(f"Found {len(flows)} forward TCP data flows:")
    for f in flows:
        print(f"  Flow {f['flowId']}: {f['throughput_kbps']:.1f} kbps, "
              f"Delay {f['mean_delay_ms']:.2f} ms, Loss {f['loss_ratio']*100:.2f}%")
    
    import os
    out_dir = os.path.dirname(xml_file) or '.'
    plot_throughput(flows, os.path.join(out_dir, 'throughput.png'))
    plot_delay(flows, os.path.join(out_dir, 'delay.png'))
    plot_loss(flows, os.path.join(out_dir, 'loss.png'))

if __name__ == "__main__":
    main()
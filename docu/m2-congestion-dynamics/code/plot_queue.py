#!/usr/bin/env python3
"""
plot_queue.py
Read the queue trace CSV (Time,QueuePackets) and plot queue occupancy over time.
"""

import sys
import csv
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 plot_queue.py <queue.csv>")
        sys.exit(1)
    csv_file = sys.argv[1]
    times = []
    qlen = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row['Time']))
            qlen.append(int(row['QueuePackets']))
    
    plt.figure(figsize=(12,4))
    plt.plot(times, qlen, linewidth=0.8, color='darkred')
    plt.xlabel('Time (s)')
    plt.ylabel('Queue occupancy (packets)')
    plt.title('Bottleneck Queue Occupancy Over Time')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    import os
    out_dir = os.path.dirname(csv_file) or '.'
    plt.savefig(os.path.join(out_dir, 'queue_occupancy.png'), dpi=150)
    plt.close()
    print(f"Queue plot saved to {os.path.join(out_dir, 'queue_occupancy.png')}")

if __name__ == "__main__":
    main()
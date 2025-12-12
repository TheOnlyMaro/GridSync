#!/usr/bin/env python3
"""
Analyze GridSync test results and generate comparison plots
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "results"
TEST_SCENARIOS = ["baseline", "loss_2", "loss_5", "delay_100ms"]


def load_test_data(scenario):
    """Load client and server CSV files for a given scenario"""
    scenario_dir = os.path.join(RESULTS_DIR, scenario)

    client_file = os.path.join(scenario_dir, "client_metrics.csv")
    server_file = os.path.join(scenario_dir, "server_metrics.csv")

    client_df = None
    server_df = None

    if os.path.exists(client_file):
        try:
            client_df = pd.read_csv(client_file)
            print(f"✓ Loaded {scenario}/client_metrics.csv ({len(client_df)} rows)")
        except Exception as e:
            print(f"✗ Error loading {scenario}/client_metrics.csv: {e}")
    else:
        print(f"✗ Missing {scenario}/client_metrics.csv")

    if os.path.exists(server_file):
        try:
            server_df = pd.read_csv(server_file)
            print(f"✓ Loaded {scenario}/server_metrics.csv ({len(server_df)} rows)")
        except Exception as e:
            print(f"✗ Error loading {scenario}/server_metrics.csv: {e}")
    else:
        print(f"✗ Missing {scenario}/server_metrics.csv")

    return client_df, server_df


def generate_comparison_plots():
    """Generate comparison plots across all test scenarios"""

    # Load all data
    all_data = {}
    for scenario in TEST_SCENARIOS:
        client_df, server_df = load_test_data(scenario)
        all_data[scenario] = {
            'client': client_df,
            'server': server_df
        }

    print("\n" + "=" * 50)
    print("Generating comparison plots...")
    print("=" * 50 + "\n")

    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('GridSync Protocol Performance Analysis', fontsize=16, fontweight='bold')

    # Plot 1: Average Latency Comparison
    ax = axes[0, 0]
    latencies = []
    labels = []
    for scenario in TEST_SCENARIOS:
        if all_data[scenario]['client'] is not None:
            df = all_data[scenario]['client']
            if 'latency_ms' in df.columns:
                latencies.append(df['latency_ms'].mean())
                labels.append(scenario.replace('_', ' ').title())

    if latencies:
        ax.bar(labels, latencies, color=['#2ecc71', '#f39c12', '#e74c3c', '#3498db'])
        ax.set_ylabel('Latency (ms)')
        ax.set_title('Average Latency by Scenario')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)

    # Plot 2: Packet Loss Percentage
    ax = axes[0, 1]
    loss_rates = []
    labels = []
    for scenario in TEST_SCENARIOS:
        if all_data[scenario]['client'] is not None:
            df = all_data[scenario]['client']
            if 'loss_percentage' in df.columns and len(df) > 0:
                loss_rates.append(df['loss_percentage'].iloc[-1])
                labels.append(scenario.replace('_', ' ').title())

    if loss_rates:
        ax.bar(labels, loss_rates, color=['#2ecc71', '#f39c12', '#e74c3c', '#3498db'])
        ax.set_ylabel('Packet Loss (%)')
        ax.set_title('Packet Loss by Scenario')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)

    # Plot 3: Average Jitter
    ax = axes[0, 2]
    jitters = []
    labels = []
    for scenario in TEST_SCENARIOS:
        if all_data[scenario]['client'] is not None:
            df = all_data[scenario]['client']
            if 'jitter_ms' in df.columns:
                jitters.append(df['jitter_ms'].mean())
                labels.append(scenario.replace('_', ' ').title())

    if jitters:
        ax.bar(labels, jitters, color=['#2ecc71', '#f39c12', '#e74c3c', '#3498db'])
        ax.set_ylabel('Jitter (ms)')
        ax.set_title('Average Jitter by Scenario')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)

    # Plot 4: Latency Over Time (line plot for each scenario)
    ax = axes[1, 0]
    colors = ['#2ecc71', '#f39c12', '#e74c3c', '#3498db']
    for i, scenario in enumerate(TEST_SCENARIOS):
        if all_data[scenario]['client'] is not None:
            df = all_data[scenario]['client']
            if 'latency_ms' in df.columns and 'timestamp_ms' in df.columns:
                # Normalize timestamps to start at 0
                time_normalized = (df['timestamp_ms'] - df['timestamp_ms'].iloc[0]) / 1000.0
                ax.plot(time_normalized, df['latency_ms'],
                        label=scenario.replace('_', ' ').title(),
                        color=colors[i], alpha=0.7, linewidth=1.5)

    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Latency (ms)')
    ax.set_title('Latency Over Time')
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 5: Ping Comparison
    ax = axes[1, 1]
    pings = []
    labels = []
    for scenario in TEST_SCENARIOS:
        if all_data[scenario]['client'] is not None:
            df = all_data[scenario]['client']
            if 'ping_ms' in df.columns:
                pings.append(df['ping_ms'].mean())
                labels.append(scenario.replace('_', ' ').title())

    if pings:
        ax.bar(labels, pings, color=['#2ecc71', '#f39c12', '#e74c3c', '#3498db'])
        ax.set_ylabel('Ping (ms)')
        ax.set_title('Average Ping by Scenario')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)

    # Plot 6: Server CPU Usage
    ax = axes[1, 2]
    cpu_usage = []
    labels = []
    for scenario in TEST_SCENARIOS:
        if all_data[scenario]['server'] is not None:
            df = all_data[scenario]['server']
            if 'cpu_percent' in df.columns:
                cpu_usage.append(df['cpu_percent'].mean())
                labels.append(scenario.replace('_', ' ').title())

    if cpu_usage:
        ax.bar(labels, cpu_usage, color=['#2ecc71', '#f39c12', '#e74c3c', '#3498db'])
        ax.set_ylabel('CPU Usage (%)')
        ax.set_title('Average Server CPU Usage')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    # Save figure
    output_file = os.path.join(RESULTS_DIR, 'performance_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved comparison plot: {output_file}")

    # Generate summary statistics table
    generate_summary_table(all_data)

    print("\n✓ Analysis complete!")


def generate_summary_table(all_data):
    """Generate a summary statistics table"""

    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    summary_rows = []

    for scenario in TEST_SCENARIOS:
        client_df = all_data[scenario]['client']
        server_df = all_data[scenario]['server']

        if client_df is not None and len(client_df) > 0:
            row = {
                'Scenario': scenario.replace('_', ' ').title(),
                'Avg Latency (ms)': f"{client_df['latency_ms'].mean():.2f}" if 'latency_ms' in client_df else 'N/A',
                'Avg Jitter (ms)': f"{client_df['jitter_ms'].mean():.2f}" if 'jitter_ms' in client_df else 'N/A',
                'Avg Ping (ms)': f"{client_df['ping_ms'].mean():.2f}" if 'ping_ms' in client_df else 'N/A',
                'Packet Loss (%)': f"{client_df['loss_percentage'].iloc[-1]:.2f}" if 'loss_percentage' in client_df else 'N/A',
                'Packets Received': f"{client_df['packets_received'].iloc[-1]}" if 'packets_received' in client_df else 'N/A',
            }

            if server_df is not None and len(server_df) > 0:
                row['Avg CPU (%)'] = f"{server_df['cpu_percent'].mean():.2f}" if 'cpu_percent' in server_df else 'N/A'
            else:
                row['Avg CPU (%)'] = 'N/A'

            summary_rows.append(row)

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        print(summary_df.to_string(index=False))

        # Save to CSV
        output_file = os.path.join(RESULTS_DIR, 'summary_statistics.csv')
        summary_df.to_csv(output_file, index=False)
        print(f"\n✓ Saved summary table: {output_file}")
    else:
        print("No data available for summary table")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    print("=" * 80)
    print("GridSync Performance Analysis")
    print("=" * 80 + "\n")

    # Create results directory if it doesn't exist
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Check if matplotlib is available
    try:
        import matplotlib

        matplotlib.use('Agg')  # Use non-interactive backend
    except ImportError:
        print("✗ Error: matplotlib is required. Install with: pip3 install matplotlib pandas")
        exit(1)

    generate_comparison_plots()
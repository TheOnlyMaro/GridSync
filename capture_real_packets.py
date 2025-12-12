#!/usr/bin/env python3
"""
Attempt to capture real packets on WSL2
"""
import subprocess
import time
import os


def capture_real():
    print("=== Attempting Real Packet Capture ===")

    # Create directory
    os.makedirs('results/baseline', exist_ok=True)
    pcap_file = 'results/baseline/real_capture.pcap'

    # Kill any existing tcpdump
    subprocess.run(['pkill', '-f', 'tcpdump'], stderr=subprocess.DEVNULL)
    time.sleep(1)

    # Find WSL2 interface (usually eth0)
    result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
    if 'eth0' in result.stdout:
        interface = 'eth0'
    elif 'lo' in result.stdout:
        interface = 'lo'
    else:
        interface = 'any'

    print(f"Using interface: {interface}")

    # Start tcpdump
    print(f"Starting tcpdump on {interface}...")
    tcpdump = subprocess.Popen([
        'sudo', 'tcpdump',
        '-i', interface,
        '-w', pcap_file,
        'port', '9999',  # Your server port
        '-s', '0'  # Capture full packets
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    time.sleep(2)

    # Run quick test
    print("Running server and client...")
    server = subprocess.Popen(['python3', 'server.py'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    time.sleep(1)

    client = subprocess.Popen(['python3', 'client.py'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)

    # Run for 30 seconds
    print("Capturing for 30 seconds...")
    time.sleep(30)

    # Stop everything
    print("Stopping...")
    client.terminate()
    server.terminate()
    tcpdump.terminate()
    time.sleep(2)

    # Check results
    if os.path.exists(pcap_file):
        size = os.path.getsize(pcap_file)
        print(f"\n✅ Capture complete!")
        print(f"   File: {pcap_file}")
        print(f"   Size: {size} bytes")

        # Try to read with tcpdump
        if size > 0:
            result = subprocess.run(['tcpdump', '-r', pcap_file, '-c', '5'],
                                    capture_output=True, text=True)
            print("\nSample packets:")
            print(result.stdout[:500])
    else:
        print("\n❌ No PCAP file created")
        print("Note: WSL2 packet capture is limited")


if __name__ == '__main__':
    capture_real()
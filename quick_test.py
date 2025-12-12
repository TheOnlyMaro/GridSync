#!/usr/bin/env python3
"""
Quick test to verify client and server can create CSV files
"""
import os
import time
import subprocess
import sys


def test_csv_generation():
    print("=" * 60)
    print("Testing CSV Generation")
    print("=" * 60)

    # Clean old files
    for f in ['client_metrics.csv', 'server_metrics.csv']:
        if os.path.exists(f):
            os.remove(f)
            print(f"Removed old {f}")

    print("\nStarting server...")
    server = subprocess.Popen(['python3', 'server.py'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    time.sleep(3)

    print("Starting client...")
    client = subprocess.Popen(['python3', 'client.py'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

    print("Running for 20 seconds...")
    time.sleep(20)

    print("Stopping processes...")
    client.terminate()
    server.terminate()
    time.sleep(2)

    client.kill()
    server.kill()
    time.sleep(1)

    # Check results
    print("\n" + "=" * 60)
    print("Results:")
    print("=" * 60)

    success = True

    if os.path.exists('client_metrics.csv'):
        size = os.path.getsize('client_metrics.csv')
        with open('client_metrics.csv', 'r') as f:
            lines = len(f.readlines())
        print(f"✓ client_metrics.csv created: {size} bytes, {lines} lines")
    else:
        print("✗ client_metrics.csv NOT FOUND")
        success = False

        # Print client stderr to debug
        client_err = client.stderr.read().decode('utf-8')
        if client_err:
            print("\nClient errors:")
            print(client_err)

    if os.path.exists('server_metrics.csv'):
        size = os.path.getsize('server_metrics.csv')
        with open('server_metrics.csv', 'r') as f:
            lines = len(f.readlines())
        print(f"✓ server_metrics.csv created: {size} bytes, {lines} lines")
    else:
        print("✗ server_metrics.csv NOT FOUND")
        success = False

        # Print server stderr to debug
        server_err = server.stderr.read().decode('utf-8')
        if server_err:
            print("\nServer errors:")
            print(server_err)

    print("=" * 60)

    if success:
        print("\n✓ SUCCESS! CSV files are being generated correctly.")
        print("\nYou can now run: ./run_tests_wsl.sh")
        return 0
    else:
        print("\n✗ FAILED! CSV files not generated.")
        print("\nTroubleshooting:")
        print("1. Check if client connects to server")
        print("2. Verify psutil is installed: pip3 install psutil")
        print("3. Look at error messages above")
        return 1


if __name__ == '__main__':
    sys.exit(test_csv_generation())
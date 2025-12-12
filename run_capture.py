import subprocess, time, os

os.makedirs("results/baseline", exist_ok=True)

# Start server
server = subprocess.Popen(
    ["python3", "server.py"],
    stdout=open("results/baseline/server.log", "w"),
    stderr=subprocess.STDOUT,
)

# Start client
client = subprocess.Popen(
    ["python3", "client.py"],
    stdout=open("results/baseline/client.log", "w"),
    stderr=subprocess.STDOUT,
)

# Start packet capture — changed 'lo' to 'eth0'
cap = subprocess.Popen(
    ["sudo", "tcpdump", "-i", "eth0", "-w", "results/baseline/capture.pcap", "udp"]
)

# Run for 60 seconds
time.sleep(60)

# Stop all processes
for p in (client, server, cap):
    try:
        p.terminate()
    except Exception:
        pass

# Give tcpdump a moment to flush
time.sleep(1)

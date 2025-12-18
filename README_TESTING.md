# GridSync Phase 3 - Testing Documentation

This document explains how to run and validate the GridSync Phase 3 test suite.

---

## Section 1: Quick Start

### Running the Complete Test Suite

1. **Run the test suite** (requires root/sudo):
   ```bash
   sudo ./run_complete_tests.sh
   ```

2. **Wait for completion**:
   - The test suite takes approximately **5 minutes** to complete
   - It runs 4 test scenarios, each lasting 60 seconds
   - You'll see status messages for each step

3. **Validate results**:
   ```bash
   ./validate_results.sh
   ```

4. **If all checks pass**:
   - You'll see "READY FOR SUBMISSION"
   - All required files are present and contain data
   - You're ready to submit your results!

---

## Section 2: What Gets Created

The test suite creates a `results/` folder with the following structure:

```
results/
├── baseline/          # No network issues (normal conditions)
├── loss_2/            # 2% packet loss simulation
├── loss_5/            # 5% packet loss simulation
└── delay_100ms/       # 100ms network delay simulation
```

### Each scenario folder contains:

1. **capture.pcap**
   - Network packet recording (PCAP format)
   - Contains all UDP packets captured on port 9999
   - **Use Wireshark** to view: `wireshark results/baseline/capture.pcap`
   - Or command line: `tcpdump -r results/baseline/capture.pcap -c 10`

2. **client_metrics.csv**
   - Performance data collected by the client
   - Contains timing, latency, packet statistics
   - Used to analyze client-side performance

3. **server_metrics.csv**
   - Performance data collected by the server
   - Contains timing, broadcast rates, client statistics
   - Used to analyze server-side performance

4. **client.log**
   - Console output from the client process
   - Shows connection status, errors, debug messages

5. **server.log**
   - Console output from the server process
   - Shows client connections, broadcast logs, errors

---

## Section 3: Understanding PCAP Files

### What is a PCAP file?

**PCAP** (Packet CAPture) is a file format that stores network traffic data. It's a recording of all network packets that passed through the network interface during the test.

### Why PCAP files matter

The Teaching Assistant (TA) uses PCAP files to verify:
- ✅ Your protocol header format (28-byte GSYN header)
- ✅ All message types (INIT, ACTION, SNAPSHOT, ACK, HEARTBEAT)
- ✅ Packet sizes and timing
- ✅ Network encapsulation (Ethernet/IP/UDP layers)
- ✅ Protocol correctness and structure

### How to view PCAP files

#### Option 1: Wireshark (Graphical)
```bash
wireshark results/baseline/capture.pcap
```
- Visual interface showing all packets
- Filter by protocol, source, destination
- View packet contents, headers, timing

#### Option 2: tcpdump (Command line)
```bash
# View first 10 packets
tcpdump -r results/baseline/capture.pcap -c 10

# View with more detail
tcpdump -r results/baseline/capture.pcap -v -c 20

# View only UDP packets on port 9999
tcpdump -r results/baseline/capture.pcap "udp port 9999" -c 10
```

### What to look for in PCAP files

- **Protocol headers**: Your 28-byte GSYN header should be visible in UDP payload
- **Message types**: INIT, ACTION, SNAPSHOT, ACK, HEARTBEAT messages
- **Packet timing**: Should match your 20Hz broadcast rate (~50ms between packets)
- **Packet sizes**: Consistent with your protocol specification

---

## Section 4: Requirements

### System Requirements

- **Operating System**: Native Linux (not WSL2)
  - WSL2 doesn't support `tc netem` properly
  - Network emulation requires native Linux networking stack

- **Permissions**: Root/sudo access required
  - Needed for `tc` (traffic control) to emulate network conditions
  - Needed for `tcpdump` to capture packets

### Required Software

#### System packages:
```bash
sudo apt-get update
sudo apt-get install iproute2 tcpdump
```

- **iproute2**: Provides `tc` command for network emulation
- **tcpdump**: Packet capture tool

#### Python packages:
```bash
pip3 install psutil matplotlib pandas
```

- **psutil**: System and process monitoring
- **matplotlib**: For generating graphs (if using analyze_results.py)
- **pandas**: Data analysis (if using analyze_results.py)

### Python Version
- **Python 3.10+** required

---

## Section 5: Troubleshooting

### Problem: "This script must be run as root"

**Solution**: Run with sudo:
```bash
sudo ./run_complete_tests.sh
```

---

### Problem: "tc (traffic control) not found"

**Solution**: Install iproute2:
```bash
sudo apt-get install iproute2
```

---

### Problem: "tcpdump not found"

**Solution**: Install tcpdump:
```bash
sudo apt-get install tcpdump
```

---

### Problem: "psutil Python module not found"

**Solution**: Install psutil:
```bash
pip3 install psutil
```

---

### Problem: Tests fail or CSV files are empty

**Possible causes**:
1. **Port conflict**: Another process is using UDP port 9999
   - Check with: `sudo netstat -ulnp | grep 9999`
   - Kill conflicting process if found

2. **Server/client crashes**: Check log files in `results/$scenario/`
   - Look at `server.log` and `client.log` for error messages

3. **Network interface issue**: Script uses `lo` (loopback)
   - Verify loopback exists: `ip link show lo`
   - Should show `UP` state

---

### Problem: "Permission denied" when running tcpdump

**Solution**: Make sure you're running as root:
```bash
sudo ./run_complete_tests.sh
```

---

### Problem: Network emulation (tc) doesn't work in WSL2

**Solution**: This is expected. WSL2 doesn't support `tc netem` properly.
- You must run tests on **native Linux** (not WSL2)
- Use a lab machine or Linux VM for full test suite

---

### Problem: validate_results.sh shows missing files

**Possible causes**:
1. Tests didn't complete successfully
   - Check if test script exited early
   - Look for error messages in output

2. CSV files weren't generated
   - Server/client may not be logging metrics
   - Check that `server.py` and `client.py` create CSV files

3. PCAP files too small
   - Packet capture may have failed
   - Check tcpdump process ran successfully

**Solution**: Re-run the test suite:
```bash
sudo ./run_complete_tests.sh
```

---

## Quick Test Script

Before running the full test suite, you can verify that client/server work:

```bash
./quick_test.sh
```

This runs a **10-second test** that:
- Starts server and client
- Checks if CSV files are created
- Shows first 3 lines of each CSV
- Verifies CSV logging is working

If this passes, the full test suite should work too!

---

## Test Scripts Overview

| Script | Purpose | Requires Root? |
|--------|---------|----------------|
| `run_complete_tests.sh` | Run all 4 test scenarios | ✅ Yes |
| `validate_results.sh` | Check all files exist | ❌ No |
| `quick_test.sh` | 10-second verification | ❌ No |

---

## Summary

1. Install dependencies (iproute2, tcpdump, Python packages)
2. Run: `sudo ./run_complete_tests.sh` (takes ~5 minutes)
3. Validate: `./validate_results.sh`
4. If "READY FOR SUBMISSION" → You're done! ✅
5. Submit the `results/` folder with all PCAP and CSV files

Good luck with Phase 3! 🚀


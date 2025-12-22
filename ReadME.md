# 🕹️ GridSync Protocol — Phase 3 Complete

**Course:** Computer Networks (Fall 2025)  
**Instructor:** Dr. Ayman Mohamed Bahaa Eldin  
**Team Members:**  
- Roaa Sherif Gadara (22P0188)  
- Ahmed Mohamed Alia (22P0273)  
- Mohamed Mohsen (22P0147)  
- Marwan Ahmed Khairy (22P0201)

---

## 📖 Overview

**GridSync v1.0** is a lightweight binary UDP-based protocol for real-time multiplayer game state synchronization.

**Key Features:**
- ✅ 28-byte binary header with CRC32 checksum
- ✅ Snapshot-based state synchronization (20 Hz broadcast rate)
- ✅ Redundant updates mechanism (last K actions per snapshot)
- ✅ Handles packet loss, reordering, and network delays
- ✅ Comprehensive metrics collection (latency, jitter, loss, CPU)

---

## ⚙️ Setup Instructions

### Requirements
- **Python 3.10+**
- **Operating System:** Native Linux (Ubuntu 20.04+)
- **Root access:** Required for network emulation (`tc`, `tcpdump`)

### Install Dependencies
```bash
# System packages
sudo apt-get update
sudo apt-get install iproute2 tcpdump

# Python packages
pip3 install psutil matplotlib pandas
```

---

## 🚀 Running the Complete Test Suite

### Quick Start
```bash
# Run all 4 test scenarios (requires root)
sudo ./run_complete_tests.sh

# Validate results
./validate_results.sh
```

### Test Scenarios
The complete test suite runs 4 scenarios (60 seconds each):
1. **Baseline** - No network impairment
2. **Loss 2%** - 2% packet loss (LAN-like)
3. **Loss 5%** - 5% packet loss (WAN-like)
4. **Delay 100ms** - 100ms network delay

### Expected Results
After ~5 minutes, you'll have:
```
results/
├── baseline/
│   ├── capture.pcap          # Network packet capture
│   ├── client_metrics.csv    # Client performance data
│   ├── server_metrics.csv    # Server performance data
│   ├── client.log            # Client console output
│   └── server.log            # Server console output
├── loss_2/                   # (same structure)
├── loss_5/                   # (same structure)
├── delay_100ms/              # (same structure)
├── performance_comparison.png
└── summary_statistics.csv
```

---

## 📊 Phase 3 Test Results

### Performance Summary
| Scenario | Avg Latency | Packet Loss | Server CPU | Status |
|----------|-------------|-------------|------------|--------|
| Baseline | 1.13 ms | 0.00% | 3.57% | ✅ Pass |
| Loss 2% | 1.76 ms | 1.79% | 4.95% | ✅ Pass |
| Loss 5% | 1.68 ms | 5.12% | 4.83% | ✅ Pass |
| Delay 100ms | 100.31 ms | 0.00% | 2.35% | ✅ Pass |

**All acceptance criteria met!** ✓

### Key Findings
- **Low Latency**: Sub-2ms latency under loss conditions
- **Efficient**: Server CPU usage remains under 5% (target: <60%)
- **Robust**: Protocol gracefully handles 5% packet loss
- **Scalable**: Delay handling works perfectly (100ms ±0.3ms)

---

## 📁 Project Structure
```
GridSync/
├── client.py              # Client implementation with metrics
├── server.py              # Server with snapshot broadcasting
├── util.py                # Protocol utilities (header, checksum)
├── config.py              # Configuration parameters
├── game.py                # Game state management
├── ui.py                  # Tkinter GUI client (optional)
├── run_complete_tests.sh  # Complete test suite (4 scenarios)
├── validate_results.sh    # Results validation script
├── analyze_results.py     # Performance analysis & plotting
├── README.md              # This file
├── README_TESTING.md      # Detailed testing documentation
└── results/               # Test results (generated)
```

---

## 🎮 Manual Testing (Optional)

### Run Server
```bash
python3 server.py
```

### Run Client (CLI)
```bash
python3 client.py
```

### Run Client (GUI)
```bash
python3 ui.py
```

---

## 📝 Protocol Specification

### Header Format (28 bytes)
```
Field           Size    Description
─────────────────────────────────────────
protocol_id     4       "GSYN" (ASCII)
version         1       Protocol version (1)
msg_type        1       Message type (0-4)
snapshot_id     4       Snapshot identifier
seq_num         4       Sequence number
timestamp       8       Unix timestamp (ms)
payload_len     2       Payload length
checksum        4       CRC32 checksum
─────────────────────────────────────────
Total:          28 bytes
```

### Message Types
- `0` INIT - Client connection request
- `1` ACTION - Player action (cell acquisition)
- `2` SNAPSHOT - Server state broadcast
- `3` ACK - Acknowledgment
- `4` HEARTBEAT - Keep-alive message

### Reliability Mechanism
**Redundant Updates:** Each snapshot includes the last K=20 actions, ensuring clients can recover from packet loss without explicit retransmission.

---

## 📺 Demo Video

**Video Link:** [Add your YouTube/Drive link here]

The demo video covers:
- Protocol header field explanation
- Packet loss and reordering handling
- PCAP analysis showing recovery mechanism
- Experimental results walkthrough

---

## 🔧 Troubleshooting

### "tc (traffic control) not found"
```bash
sudo apt-get install iproute2
```

### "tcpdump not found"
```bash
sudo apt-get install tcpdump
```

### "Permission denied"
Run test script with sudo:
```bash
sudo ./run_complete_tests.sh
```

### Tests completed on Native Linux
**Note:** This project was tested on native Linux (Ubuntu 20.04).  
WSL2 does not support `tc netem` - use native Linux for network emulation.

---

## 📚 Deliverables
✅ **Implementation:** Client, Server, Protocol (complete)  
✅ **Testing Scripts:** Automated test suite (complete)  
✅ **Results & Plots:** Performance analysis (complete)  
✅ **PCAP Files:** Network captures (complete)  
⏳ **Mini-RFC:** Protocol specification document (in progress)  
⏳ **Technical Report:** Experimental analysis (in progress)  
⏳ **Demo Video:** Protocol demonstration (in progress)

---

## 👥 Team Contributions
All team members contributed equally to design, implementation, testing, and documentation.

---

## 📄 License
This project is submitted as coursework for Computer Networks (Fall 2025).
# 🕹️ GridSync Protocol — Phase 1 Prototype  
**Course:** Computer Networks (Fall 2025)  
**Instructor:** Dr. Ayman Mohamed Bahaa Eldin  
**Team Members:**  
- Roaa Sherif Gadara (22P0188)  
- Ahmed Mohamed Alia (22P0273)  
- Mohamed Mohsen (22P0147)  
- Marwan Ahmed Khairy (22P0201)

---

## 📖 Overview

**GridSync v1.0** is a lightweight binary UDP-based protocol that synchronizes the game grid state between a **server** and multiple **clients** in real-time.

It implements:
- INIT → ACK → ACTION → SNAPSHOT exchange  
- 28-byte fixed binary header  
- Real-time updates (20 Hz broadcast rate)  
- UDP communication for low latency  

✅ Fully meets **Phase 1** requirements:
> “Working prototype demonstrating INIT and DATA exchanges over UDP (server + client).”

---

## ⚙️ Setup Instructions

### 🧠 Requirements
- **Python 3.10+**  
- Works on **Windows**, **macOS**, and **Linux**  
- No extra libraries needed (uses only `socket`, `threading`, and `struct`)

### 🪄 Run Everything in PyCharm
1. Open **PyCharm** → Open Folder → select `GridSync_Phase1/`  
2. Make sure both files exist:  
   - `server.py`  
   - `client.py`
3. Click **Run ▶️** beside `server.py` → this starts the server.  
4. Then **Run ▶️** beside `client.py` → this starts the client.  

You’ll instantly see the connection handshake.

---

## 🖥️ Running from Command Prompt (Manual Option)

### Start the Server
```bash
python server.py
python client.py

## 📊 Phase 2 - Testing & Metrics

### Quick Start
```bash
# Install dependencies
pip3 install psutil matplotlib pandas

# Run baseline test
chmod +x run_tests_wsl.sh
./run_tests_wsl.sh

# View results
cat results/summary_statistics.csv
```

### Test Results (Baseline)
- **Latency**: 0.39 ms average (was 0.37 ms)
- **Packet Loss**: 0.00% (was 0.23%)
- **Server CPU**: 13.90% (was 11.44%)
- **Packets**: 427 received in 60 seconds
### Files Generated
- `results/baseline/client_metrics.csv` - Client performance data
- `results/baseline/server_metrics.csv` - Server performance data
- `results/performance_comparison.png` - Visual analysis
- `results/summary_statistics.csv` - Summary table

### Known Limitations
- WSL2 does not support `tc netem` for network emulation
- Full packet loss/delay tests require native Linux
- See `PHASE2_NOTES.md` for detailed report

### PCAP Generation Note

**WSL2 Limitation:** Due to WSL2's virtual networking, real packet capture 
is unreliable. The provided PCAP files contain **simulated packets** that 
accurately represent the GridSync protocol structure.

**What the simulated PCAP demonstrates:**
- ✅ Correct 28-byte GSYN header format
- ✅ All 5 message types (INIT, ACTION, SNAPSHOT, ACK, HEARTBEAT)
- ✅ Proper network encapsulation (Ethernet/IP/UDP)
- ✅ Realistic timing (20Hz broadcast rate)

**Real performance data** is captured in the CSV files:
- `results/baseline/client_metrics.csv` - Client-side measurements
- `results/baseline/server_metrics.csv` - Server-side measurements

**For Phase 3:** Full packet capture will be performed on native Linux
lab machines using `tcpdump` with proper network emulation.
### For Phase 3
Complete test suite will be run on lab machines with:
- 2% and 5% packet loss scenarios
- 100ms delay scenario
- Packet capture (pcap) files
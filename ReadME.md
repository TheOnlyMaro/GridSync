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


"""
Configuration file for GSYN network protocol client and server.
Modify these variables to change behavior without editing client.py or server.py
"""

# ========== SERVER CONFIGURATION ==========
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9999
SERVER_RUN_DURATION = 20  # seconds; set to float('inf') for indefinite runtime

# ========== CLIENT CONFIGURATION ==========
CLIENT_SERVER_HOST = "154.176.96.42"
CLIENT_SERVER_PORT = 9999
CLIENT_HEARTBEAT_INTERVAL = 1.0  # seconds between heartbeat sends
CLIENT_HEARTBEAT_TIMEOUT = 3.0  # seconds before disconnection if no ACK

# ========== PROTOCOL CONFIGURATION ==========
HEARTBEAT_INTERVAL = 0.05  # seconds; server-side heartbeat broadcast interval
HEARTBEAT_TIMEOUT = 3.0  # seconds; server marks client inactive if no ACK in this time

# ========== SNAPSHOT & ACTION UPDATES ==========
SNAPSHOT_BROADCAST_INTERVAL = 0.05  # seconds between snapshot broadcasts
LAST_K_ACTIONS = 20  # number of recent actions to include in snapshots

# ========== GRID CONFIGURATION ==========
GRID_SIZE = 25  # 20x20 grid

# ========== SOCKET CONFIGURATION ==========
SOCKET_TIMEOUT = 0.5  # seconds; socket timeout for recv operations
SOCKET_BUFFER_SIZE = 2048  # bytes; UDP receive buffer size

# ========== UDP RECEIVE BUFFER ==========
MAX_RECV_SIZE = 4096  # bytes; max data size to receive per recvfrom call

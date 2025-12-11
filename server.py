import socket
import struct
import time
import threading
from util import pack_header, pack_actions_payload, MSG_INIT, MSG_ACTION, MSG_SNAPSHOT, MSG_ACK, MSG_HEARTBEAT, check_auth
from game import GridGame
from config import SERVER_HOST, SERVER_PORT, SERVER_RUN_DURATION, HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, SNAPSHOT_BROADCAST_INTERVAL, LAST_K_ACTIONS, GRID_SIZE, SOCKET_TIMEOUT, PACKET_LIFETIME, MAX_PLAYERS

SERVER_ADDR = (SERVER_HOST, SERVER_PORT)

# Client dictionary: addr -> {player_id, seq_num, last_seen, state}
clients = {}
snapshot_id = 0
running = True
next_player_id = 1

# Game logic
game = GridGame(GRID_SIZE, GRID_SIZE)

def _register_client(addr):
    """Register a new client address and return the client_data dict and player_id."""
    global next_player_id
    player_id = next_player_id
    next_player_id += 1
    clients[addr] = {
        'player_id': player_id,
        'seq_num': 1,
        'last_recv_seq': 0,
        'last_seen': time.time(),
        'last_heartbeat_recv': time.time(),
        'state': 'active'
    }
    return clients[addr], player_id


def _send_full_snapshot_to_client(sock, addr, client_data):
    """Send a full-action snapshot to the given client address."""
    global snapshot_id
    try:
        full_payload = pack_actions_payload(game.actions)
        snapshot_id += 1
        header = pack_header(MSG_SNAPSHOT, snapshot_id, client_data['seq_num'], len(full_payload))
        sock.sendto(header + full_payload, addr)
        client_data['seq_num'] += 1
        print(f"[SERVER] Sent FULL SNAPSHOT #{snapshot_id} to Player {client_data['player_id']} (actions: {len(game.actions)})")
    except Exception:
        pass


def _process_existing_client_packet(sock, addr, data, msg_type, heartbeat_id, seq_num, timestamp_ms):
    """Process a packet from a client that is already registered."""
    client_data = clients[addr]
    player_id = client_data['player_id']

    # drop duplicate or older seqs
    if seq_num <= client_data.get('last_recv_seq', 0):
        return

    # drop stale packets
    now_ms = int(time.time() * 1000)
    if now_ms - timestamp_ms > int(PACKET_LIFETIME * 1000):
        return

    # accept and update last recv seq
    client_data['last_recv_seq'] = seq_num

    # If client is inactive and sends anything, deliver full actions snapshot (do not re-activate)
    if client_data.get('state') == 'inactive':
        print(f"[SERVER] Inactive client {player_id} sent data — sending full actions snapshot")
        _send_full_snapshot_to_client(sock, addr, client_data)
        return

    # For active clients, update last_seen
    client_data['last_seen'] = time.time()

    if msg_type == MSG_ACTION:
        _handle_action_message(player_id, data)
    elif msg_type == MSG_ACK:
        # ACK from client (rare) - update last_seen as a soft touch and reactivate
        client_data['last_seen'] = time.time()
        if client_data.get('state') == 'inactive':
            client_data['state'] = 'active'
            print(f"[SERVER] Received ACK from Player {player_id} → re-activated")
    elif msg_type == MSG_HEARTBEAT:
        # Client sent heartbeat (unidirectional): update last heartbeat receive time
        client_data['last_heartbeat_recv'] = time.time()
        # Reply with ACK that contains same heartbeat id in snapshot_id field
        header = pack_header(MSG_ACK, heartbeat_id, client_data['seq_num'], 0)
        try:
            sock.sendto(header, addr)
            client_data['seq_num'] += 1
        except Exception:
            pass


def _handle_action_message(player_id, data):
    try:
        row, col = struct.unpack("!HH", data[28:32])
        if game.grid[row][col] != 0:
            print(f"[SERVER] ACTION rejected from Player {player_id} → Cell ({row},{col}) occupied")
        elif game.apply_action(player_id, row, col):
            print(f"[SERVER] ACTION from Player {player_id} → Cell ({row},{col})")
        else:
            print(f"[SERVER] Invalid cell ({row},{col}) from Player {player_id}")
    except Exception:
        pass


def handle_client(sock):
    """Main loop: receive and dispatch incoming packets."""
    global snapshot_id, next_player_id
    while running:
        try:
            data, addr = sock.recvfrom(2048)
            # Validate header/auth before processing
            ok, reason = check_auth(data[:28])
            if not ok:
                # ignore invalid packets
                continue

            msg_type = data[5]
            # parse heartbeat_id, seq and timestamp for validation
            heartbeat_id = struct.unpack("!I", data[6:10])[0]
            seq_num = struct.unpack("!I", data[10:14])[0]
            timestamp_ms = struct.unpack("!Q", data[14:22])[0]

            if addr not in clients:
                # Only register new client on explicit INIT message
                if msg_type != MSG_INIT:
                    continue
                # Check if we've reached max players
                if len(clients) >= MAX_PLAYERS:
                    print(f"[SERVER] INIT from {addr} rejected: max players ({MAX_PLAYERS}) reached")
                    continue
                client_data, player_id = _register_client(addr)
                print(f"[SERVER] INIT from {addr} → Player {player_id}")
                # send ACK for INIT
                header = pack_header(MSG_ACK, 0, client_data['seq_num'], 0)
                sock.sendto(header, addr)
                client_data['seq_num'] += 1
                # send full history snapshot to late-joining client
                _send_full_snapshot_to_client(sock, addr, client_data)
                continue
            else:
                _process_existing_client_packet(sock, addr, data, msg_type, heartbeat_id, seq_num, timestamp_ms)

        except socket.timeout:
            continue
        except Exception:
            break

# New heartbeat thread: sends heartbeat to active clients and marks inactive if no ACK in timeout seconds
def heartbeat(sock, interval=HEARTBEAT_INTERVAL, timeout=HEARTBEAT_TIMEOUT):
    while running:
        now = time.time()
        for addr, cdata in list(clients.items()):
            # Monitor last received heartbeat time and mark clients inactive
            last_recv = cdata.get('last_heartbeat_recv', 0)
            if now - last_recv > timeout and cdata.get('state') == 'active':
                cdata['state'] = 'inactive'
                print(f"[SERVER] Client Player {cdata['player_id']} marked INACTIVE (no heartbeat received in {timeout}s)")
        time.sleep(interval)


def broadcast_snapshots(sock):
    global snapshot_id
    last_payload = None
    while running:
        time.sleep(SNAPSHOT_BROADCAST_INTERVAL)
        if not clients:
            continue
        
        # Get the last K actions via game logic
        recent_actions = game.get_recent_actions(LAST_K_ACTIONS)
        # Pack payload using util helper
        payload = pack_actions_payload(recent_actions)
        
        # Only increment snapshot_id if payload changed
        if payload != last_payload:
            snapshot_id += 1
            last_payload = payload
        
        inactiveClients = 0
        for addr in clients:
            if(clients[addr].get('state') == 'inactive'):
                inactiveClients += 1
                continue  # Skip inactive clients
            header = pack_header(MSG_SNAPSHOT, snapshot_id, clients[addr]['seq_num'], len(payload))
            sock.sendto(header + payload, addr)
            clients[addr]['seq_num'] += 1
        
        print(f"[SERVER] Sent SNAPSHOT #{snapshot_id} to {len(clients) - inactiveClients} clients (actions: {len(recent_actions)})")

def main():
    global running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SERVER_ADDR)
    sock.settimeout(SOCKET_TIMEOUT)

    print(f"[SERVER] Listening on {SERVER_ADDR[0]}:{SERVER_ADDR[1]}")
    threading.Thread(target=broadcast_snapshots, args=(sock,), daemon=True).start()
    threading.Thread(target=heartbeat, args=(sock,), daemon=True).start()

    start_time = time.time()
    try:
        while time.time() - start_time < SERVER_RUN_DURATION:
            handle_client(sock)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        sock.close()
        print("[SERVER] Shutting down...")

if __name__ == "__main__":
    main()

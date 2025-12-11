import socket
import struct
import time
import threading
from util import pack_header, pack_actions_payload, MSG_INIT, MSG_ACTION, MSG_SNAPSHOT, MSG_ACK, MSG_HEARTBEAT, check_auth
from game import GridGame

SERVER_ADDR = ("0.0.0.0", 9999)

# Client dictionary: addr -> {player_id, seq_num, last_seen, state}
clients = {}
snapshot_id = 0
running = True
next_player_id = 1

# Game logic
game = GridGame(20, 20)

def handle_client(sock):
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
            if addr not in clients:
                # Only register new client on explicit INIT message
                if msg_type != MSG_INIT:
                    continue
                # Register new client with dictionary structure
                player_id = next_player_id
                next_player_id += 1
                clients[addr] = {
                    'player_id': player_id,
                    'seq_num': 0,
                    'last_seen': time.time(),
                    'last_heartbeat_ack': time.time(),
                    'state': 'active'
                }
                print(f"[SERVER] INIT from {addr} → Player {player_id}")
                header = pack_header(MSG_ACK, 0, clients[addr]['seq_num'], 0)
                sock.sendto(header, addr)
                continue
            else:
                # Update existing client
                client_data = clients[addr]
                player_id = client_data['player_id']
                # If client is inactive and sends anything, deliver full actions snapshot (do not re-activate)
                if client_data.get('state') == 'inactive':
                    print(f"[SERVER] Inactive client {player_id} sent data — sending full actions snapshot")
                    full_payload = pack_actions_payload(game.actions)
                    header = pack_header(MSG_SNAPSHOT, snapshot_id, client_data['seq_num'], len(full_payload))
                    try:
                        sock.sendto(header + full_payload, addr)
                    except Exception:
                        pass
                    # Do not update state or last_seen here; only ACK will reactivate
                    continue

                # For active clients, update last_seen
                client_data['last_seen'] = time.time()

                if msg_type == MSG_ACTION:
                    # Expecting row,col starting at header length (28)
                    row, col = struct.unpack("!HH", data[28:32])
                    # Apply via game logic
                    if game.apply_action(player_id, row, col):
                        print(f"[SERVER] ACTION from Player {player_id} → Cell ({row},{col})")
                    else:
                        print(f"[SERVER] Invalid cell ({row},{col}) from Player {player_id}")
                elif msg_type == MSG_ACK:
                    # ACK can be used to acknowledge heartbeats/snapshots - reactivate client if it was inactive
                    client_data['last_heartbeat_ack'] = time.time()
                    if client_data.get('state') == 'inactive':
                        client_data['state'] = 'active'
                        print(f"[SERVER] Received ACK from Player {player_id} → re-activated")
                elif msg_type == MSG_HEARTBEAT:
                    # If client explicitly replies with heartbeat message type, treat similarly to ACK
                    client_data['last_heartbeat_ack'] = time.time()
                # else: ignore or handle other message types as needed

        except socket.timeout:
            continue
        except Exception as e:
            break

# New heartbeat thread: sends heartbeat to active clients and marks inactive if no ACK in 3s
def heartbeat(sock, interval=0.05, timeout=3.0):
    while running:
        now = time.time()
        for addr, cdata in list(clients.items()):
            # Send heartbeat only to clients currently marked active
            if cdata.get('state') == 'active':
                header = pack_header(MSG_HEARTBEAT, 0, cdata['seq_num'], 0)
                try:
                    sock.sendto(header, addr)
                except Exception:
                    pass
                # If last heartbeat ack is too old, mark inactive
                last_ack = cdata.get('last_heartbeat_ack', 0)
                if now - last_ack > timeout:
                    cdata['state'] = 'inactive'
                    print(f"[SERVER] Client Player {cdata['player_id']} marked INACTIVE (no heartbeat ACK in {timeout}s)")
        time.sleep(interval)


def broadcast_snapshots(sock):
    global snapshot_id
    last_payload = None
    while running:
        time.sleep(0.05)
        if not clients:
            continue
        
        # Get the last 20 actions via game logic
        recent_actions = game.get_recent_actions(20)
        # Pack payload using util helper
        payload = pack_actions_payload(recent_actions)
        
        # Only increment snapshot_id if payload changed
        if payload != last_payload:
            snapshot_id += 1
            last_payload = payload
        
        for addr in clients:
            if(clients[addr].get('state') == 'inactive'):
                continue  # Skip inactive clients
            header = pack_header(MSG_SNAPSHOT, snapshot_id, clients[addr]['seq_num'], len(payload))
            sock.sendto(header + payload, addr)
            clients[addr]['seq_num'] += 1
        
        print(f"[SERVER] Sent SNAPSHOT #{snapshot_id} to {len(clients)} clients (actions: {len(recent_actions)})")

def main():
    global running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SERVER_ADDR)
    sock.settimeout(0.5)

    print(f"[SERVER] Listening on {SERVER_ADDR[0]}:{SERVER_ADDR[1]}")
    threading.Thread(target=broadcast_snapshots, args=(sock,), daemon=True).start()
    threading.Thread(target=heartbeat, args=(sock,), daemon=True).start()

    start_time = time.time()
    try:
        while time.time() - start_time < 20:  # run for 20 seconds
            handle_client(sock)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        sock.close()
        print("[SERVER] Shutting down...")

if __name__ == "__main__":
    main()

import socket
import struct
import time
import threading
import csv
import os
import psutil
from util import pack_header, pack_actions_payload, MSG_INIT, MSG_ACTION, MSG_SNAPSHOT, MSG_ACK, MSG_HEARTBEAT, check_auth
from game import GridGame
from config import SERVER_HOST, SERVER_PORT, SERVER_RUN_DURATION, SNAPSHOT_BROADCAST_INTERVAL, LAST_K_ACTIONS, GRID_SIZE, SOCKET_TIMEOUT, PACKET_LIFETIME, MAX_PLAYERS

SERVER_ADDR = (SERVER_HOST, SERVER_PORT)
MAXFOURBYTE = 0xFFFFFFFF

clients = {}
snapshot_id = 0
running = True
next_player_id = 1

game = GridGame(GRID_SIZE, GRID_SIZE)

# CSV metrics tracking
csv_file = "server_metrics.csv"
csv_initialized = False
csv_lock = threading.Lock()


def _register_client(addr):
    global next_player_id
    player_id = next_player_id
    next_player_id += 1
    clients[addr] = {
        'player_id': player_id,
        'seq_num': 1,
        'last_recv_seq': 0,
        'last_seen': time.time(),
        'last_heartbeat_recv': time.time(),
        'state': 'pending'
    }
    print(f"[SERVER] Registered new client {addr} as Player {player_id}, pending ack")
    return clients[addr], player_id


def _send_full_snapshot_to_client(sock, addr, client_data):
    try:
        full_payload = pack_actions_payload(game.actions)
        header = pack_header(MSG_SNAPSHOT, MAXFOURBYTE, client_data['seq_num'], len(full_payload))
        sock.sendto(header + full_payload, addr)
        client_data['seq_num'] += 1
        print(f"[SERVER] Sent FULL SNAPSHOT #{MAXFOURBYTE} to Player {client_data['player_id']} (actions: {len(game.actions)})")
    except Exception:
        pass


def _process_existing_client_packet(sock, addr, data, msg_type, heartbeat_id, seq_num, timestamp_ms):
    client_data = clients[addr]
    player_id = client_data['player_id']

    if seq_num <= client_data.get('last_recv_seq', 0):
        return

    now_ms = int(time.time() * 1000)
    if now_ms - timestamp_ms > int(PACKET_LIFETIME * 1000):
        return

    client_data['last_recv_seq'] = seq_num

    if client_data.get('state') == 'pending':
        if msg_type == MSG_ACK:
            client_data['state'] = 'active'
            client_data['last_seen'] = time.time()
            print(f"[SERVER] Received ACK from Player {player_id} → activated")
        else:
            _send_full_snapshot_to_client(sock, addr, client_data)
        return

    if client_data.get('state') == 'inactive':
        print(f"[SERVER] Inactive client {player_id} sent data — sending full actions snapshot")
        _send_full_snapshot_to_client(sock, addr, client_data)
        client_data['last_seen'] = time.time()
        client_data['state'] = 'pending'
        return

    client_data['last_seen'] = time.time()

    if msg_type == MSG_ACTION:
        _handle_action_message(player_id, data)

    elif msg_type == MSG_HEARTBEAT:
        client_data['last_heartbeat_recv'] = time.time()
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
    global snapshot_id, next_player_id
    while running:
        try:
            data, addr = sock.recvfrom(2048)
            ok, reason = check_auth(data[:28])
            if not ok:
                continue

            msg_type = data[5]
            heartbeat_id = struct.unpack("!I", data[6:10])[0]
            seq_num = struct.unpack("!I", data[10:14])[0]
            timestamp_ms = struct.unpack("!Q", data[14:22])[0]

            if addr not in clients:
                if msg_type != MSG_INIT:
                    continue
                if len(clients) >= MAX_PLAYERS:
                    print(f"[SERVER] INIT from {addr} rejected: max players ({MAX_PLAYERS}) reached")
                    continue
                client_data, player_id = _register_client(addr)
                print(f"[SERVER] INIT from {addr} → Player {player_id}")
                header = pack_header(MSG_ACK, 0, client_data['seq_num'], 0)
                sock.sendto(header, addr)
                client_data['seq_num'] += 1
                _send_full_snapshot_to_client(sock, addr, client_data)
                continue
            else:
                _process_existing_client_packet(sock, addr, data, msg_type, heartbeat_id, seq_num, timestamp_ms)

        except socket.timeout:
            continue
        except Exception:
            break


def _log_server_metrics_to_csv(snapshot_id, active_clients, total_actions):
    """Log server metrics to CSV file."""
    global csv_file, csv_initialized, csv_lock

    with csv_lock:
        if not csv_initialized:
            file_exists = os.path.exists(csv_file)
            with open(csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'timestamp_ms', 'snapshot_id', 'active_clients',
                        'total_actions', 'cpu_percent'
                    ])
                f.flush()  # ADD THIS LINE
                os.fsync(f.fileno())  # ADD THIS LINE TOO
            csv_initialized = True

        timestamp_ms = int(time.time() * 1000)
        cpu_percent = psutil.cpu_percent()

        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp_ms, snapshot_id, active_clients,
                total_actions, cpu_percent
            ])


def broadcast_snapshots(sock):
    global snapshot_id
    last_payload = None
    while running:
        time.sleep(SNAPSHOT_BROADCAST_INTERVAL)
        if not clients:
            continue

        recent_actions = game.get_recent_actions(LAST_K_ACTIONS)
        payload = pack_actions_payload(recent_actions)

        # if payload != last_payload:  # COMMENT THIS LINE
        snapshot_id += 1
        last_payload = payload

        active_count = 0
        for addr in clients:
            if clients[addr].get('state') == 'inactive':
                continue
            elif clients[addr].get('state') == 'pending':
                _send_full_snapshot_to_client(sock, addr, clients[addr])
                continue

            header = pack_header(MSG_SNAPSHOT, snapshot_id, clients[addr]['seq_num'], len(payload))
            sock.sendto(header + payload, addr)
            clients[addr]['seq_num'] += 1
            active_count += 1

        print(f"[SERVER] Sent SNAPSHOT #{snapshot_id} to {active_count} clients (actions: {len(recent_actions)})")

        # Log metrics to CSV
        _log_server_metrics_to_csv(snapshot_id, active_count, len(game.actions))


def main():
    global running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SERVER_ADDR)
    sock.settimeout(SOCKET_TIMEOUT)

    print(f"[SERVER] Listening on {SERVER_ADDR[0]}:{SERVER_ADDR[1]}")
    threading.Thread(target=broadcast_snapshots, args=(sock,), daemon=True).start()

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
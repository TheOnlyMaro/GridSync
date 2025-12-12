import socket
import struct
import threading
import time
import csv
import os
from util import pack_header, MSG_INIT, MSG_ACTION, MSG_SNAPSHOT, MSG_ACK, MSG_HEARTBEAT, check_auth
from config import CLIENT_SERVER_HOST, CLIENT_SERVER_PORT, CLIENT_HEARTBEAT_INTERVAL, CLIENT_HEARTBEAT_TIMEOUT, \
    GRID_SIZE, MAX_RECV_SIZE, PACKET_LIFETIME
import logging

MAXFOURBYTE = 0xFFFFFFFF

logging.basicConfig(level=logging.INFO, format='[CLIENT] %(message)s')
logger = logging.getLogger('gsyn.client')

SERVER_ADDR = (CLIENT_SERVER_HOST, CLIENT_SERVER_PORT)


class Client:
    def __init__(self, server_addr=SERVER_ADDR, heartbeat_interval=CLIENT_HEARTBEAT_INTERVAL,
                 heartbeat_timeout=CLIENT_HEARTBEAT_TIMEOUT):
        self.server_addr = server_addr
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)

        self.running = False
        self.state = 'disconnected'

        self.seq = 1
        self.seq_lock = threading.Lock()

        self.last_heartbeat_ack = 0.0
        self.last_recv_time = 0.0
        self.last_seq_received = 0
        self.last_recv_timestamp_ms = 0
        self.last_snapshot_id = 0

        # Ping & packet loss tracking
        self.sent_packets = {}
        self.sent_packets_lock = threading.Lock()
        self.ping_ms = 0.0
        self.ping_samples = []
        self.heartbeat_id = 1
        self.heartbeat_lock = threading.Lock()
        self.pending_heartbeats = {}
        self.pending_heartbeats_lock = threading.Lock()
        self.expected_next_recv_seq = 1
        self.packets_lost = 0
        self.packets_received = 0
        self.recv_stats_lock = threading.Lock()

        # CSV metrics tracking
        self.client_id = 1
        self.csv_file = "client_metrics.csv"
        self.csv_initialized = False
        self.csv_lock = threading.Lock()
        self.previous_latency_ms = None

        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.last_grid_update = 0.0
        self.actions = []
        logger.info(f'created client; server={self.server_addr} grid={GRID_SIZE}x{GRID_SIZE}')

    def _send(self, data):
        try:
            self.sock.sendto(data, self.server_addr)
            try:
                if len(data) >= 14:
                    seq = struct.unpack('!I', data[10:14])[0]
                    now_ms = int(time.time() * 1000)
                    with self.sent_packets_lock:
                        self.sent_packets[seq] = now_ms
                    msg_type = data[5]
                    logger.info(f'sent msg_type={msg_type} seq={seq} bytes={len(data)}')
                else:
                    logger.info(f'sent {len(data)} bytes')
            except Exception:
                logger.info(f'sent {len(data)} bytes')
        except Exception:
            pass

    def send_init(self):
        with self.seq_lock:
            s = self.seq
            self.seq += 1
        header = pack_header(MSG_INIT, 0, s, 0)
        logger.info(f'sending INIT seq={s}')
        self._send(header)
        self.state = 'connecting'

    def send_action(self, row, col):
        if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
            return
        with self.seq_lock:
            s = self.seq
            self.seq += 1
        payload = struct.pack("!HH", row, col)
        header = pack_header(MSG_ACTION, 0, s, len(payload))
        logger.info(f'sending ACTION seq={s} row={row} col={col}')
        self._send(header + payload)

    def send_ack(self):
        with self.seq_lock:
            s = self.seq
            self.seq += 1
        header = pack_header(MSG_ACK, 0, s, 0)
        logger.info(f'sending ACK seq={s}')
        self._send(header)

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        self.send_init()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass

    def _listen_loop(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(MAX_RECV_SIZE)
            except socket.timeout:
                continue
            except Exception:
                break

            self.last_recv_time = time.time()
            if len(data) < 28:
                continue
            ok, reason = check_auth(data[:28])
            if not ok:
                logger.warning(f'packet rejected: {reason}')
                continue

            msg_type = data[5]
            snapshot_id = struct.unpack("!I", data[6:10])[0]
            seq_num = struct.unpack("!I", data[10:14])[0]
            timestamp_ms = struct.unpack("!Q", data[14:22])[0]

            if seq_num <= self.last_seq_received:
                logger.info(f'dropping packet seq={seq_num} <= last_seq={self.last_seq_received}')
                continue
            now_ms = int(time.time() * 1000)
            if now_ms - timestamp_ms > int(PACKET_LIFETIME * 1000):
                logger.info(f'dropping packet seq={seq_num} stale by {now_ms - timestamp_ms}ms')
                continue

            self.last_seq_received = seq_num
            self.last_recv_timestamp_ms = timestamp_ms

            with self.recv_stats_lock:
                if seq_num > self.expected_next_recv_seq:
                    gap = seq_num - self.expected_next_recv_seq
                    self.packets_lost += gap
                    logger.info(
                        f'packet loss detected: gap of {gap} (expected {self.expected_next_recv_seq}, got {seq_num})')
                self.expected_next_recv_seq = seq_num + 1
                self.packets_received += 1

            if msg_type == MSG_ACK:
                self._handle_ack(snapshot_id)
            elif msg_type == MSG_SNAPSHOT:
                self._handle_snapshot(data, snapshot_id, seq_num, timestamp_ms, now_ms)

    def _heartbeat_loop(self):
        self.last_heartbeat_ack = time.time()
        while self.running:
            now = time.time()
            if self.state != 'disconnected':
                with self.seq_lock:
                    s = self.seq
                    self.seq += 1
                with self.heartbeat_lock:
                    self.heartbeat_id += 1
                    hb_id = self.heartbeat_id
                hb = pack_header(MSG_HEARTBEAT, hb_id, s, 0)
                now_ms = int(time.time() * 1000)
                with self.pending_heartbeats_lock:
                    self.pending_heartbeats[hb_id] = now_ms
                self._send(hb)
                if now - self.last_heartbeat_ack > self.heartbeat_timeout and self.heartbeat_id > 2:
                    self.state = 'disconnected'
                    logger.warning('heartbeat timeout — disconnected from server')
            elif self.state == 'disconnected':
                self.send_init()
            time.sleep(self.heartbeat_interval)

    def _handle_ack(self, snapshot_id):
        now_ms = int(time.time() * 1000)
        hb_id = snapshot_id
        handled_hb = False
        if hb_id != 0:
            with self.pending_heartbeats_lock:
                if hb_id in self.pending_heartbeats:
                    sent_time = self.pending_heartbeats.pop(hb_id)
                    ping = now_ms - sent_time
                    self.ping_samples.append(ping)
                    if len(self.ping_samples) > 10:
                        self.ping_samples.pop(0)
                    self.ping_ms = sum(self.ping_samples) / len(self.ping_samples)
                    logger.info(f'ping (heartbeat): {ping}ms (avg: {self.ping_ms:.1f}ms)')
                    self.last_heartbeat_ack = time.time()
                    handled_hb = True

        if not handled_hb:
            self.state = 'connecting'
            logger.info(f'ACK received (for INIT) snapshot={snapshot_id}')

    def _handle_snapshot(self, data, snapshot_id, seq_num, timestamp_ms, now_ms):
        if snapshot_id == MAXFOURBYTE:
            logger.info(f'FULL SNAPSHOT received id={snapshot_id} seq={seq_num}')
            self.state = 'connected'
            self.send_ack()

        if self.state == 'disconnected':
            self.send_init()
            return

        if self.state == 'connecting':
            return

        if snapshot_id <= self.last_snapshot_id and snapshot_id != MAXFOURBYTE:
            logger.info(f'dropping SNAPSHOT id={snapshot_id} <= last_id={self.last_snapshot_id}')
            return

        self.last_snapshot_id = snapshot_id if snapshot_id != MAXFOURBYTE else self.last_snapshot_id

        payload_len = struct.unpack("!H", data[22:24])[0]
        payload = data[28:28 + payload_len] if payload_len > 0 else b''
        count = 0
        if payload:
            try:
                count = struct.unpack("!H", payload[:2])[0]
                offset = 2
                for i in range(count):
                    if offset + 6 > len(payload):
                        break
                    row, col, player_id = struct.unpack("!H H H", payload[offset:offset + 6])
                    offset += 6
                    if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                        self.grid[row][col] = player_id
            except Exception:
                pass

        self.last_grid_update = time.time()
        logger.info(f'SNAPSHOT received id={snapshot_id} seq={seq_num} actions={count}')

        # Log metrics to CSV
        self._log_metrics_to_csv(snapshot_id, seq_num, timestamp_ms, now_ms)

    def _log_metrics_to_csv(self, snapshot_id, seq_num, server_timestamp_ms, recv_time_ms):
        """Log metrics to CSV file when a SNAPSHOT is received."""
        with self.csv_lock:
            if not self.csv_initialized:
                file_exists = os.path.exists(self.csv_file)
                with open(self.csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow([
                            'timestamp_ms', 'client_id', 'snapshot_id', 'seq_num',
                            'server_timestamp_ms', 'recv_time_ms', 'latency_ms',
                            'jitter_ms', 'packets_received', 'packets_lost',
                            'loss_percentage', 'ping_ms'
                        ])
                    f.flush()  # ADD THIS LINE
                    os.fsync(f.fileno())  # ADD THIS LINE TOO
                self.csv_initialized = True

            timestamp_ms = int(time.time() * 1000)
            latency_ms = recv_time_ms - server_timestamp_ms

            jitter_ms = 0.0
            if self.previous_latency_ms is not None:
                jitter_ms = abs(latency_ms - self.previous_latency_ms)
            self.previous_latency_ms = latency_ms

            with self.recv_stats_lock:
                packets_received = self.packets_received
                packets_lost = self.packets_lost
                total_packets = packets_received + packets_lost
                loss_percentage = (packets_lost / total_packets * 100.0) if total_packets > 0 else 0.0

            ping_ms = self.ping_ms

            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp_ms, self.client_id, snapshot_id, seq_num,
                    server_timestamp_ms, recv_time_ms, latency_ms,
                    jitter_ms, packets_received, packets_lost,
                    loss_percentage, ping_ms
                ])


if __name__ == '__main__':
    c = Client()
    c.start()
    try:
        start = time.time()
        while time.time() - start < 20:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        c.stop()
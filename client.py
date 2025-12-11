import socket
import struct
import threading
import time
from util import pack_header, MSG_INIT, MSG_ACTION, MSG_SNAPSHOT, MSG_ACK, MSG_HEARTBEAT, check_auth
from config import CLIENT_SERVER_HOST, CLIENT_SERVER_PORT, CLIENT_HEARTBEAT_INTERVAL, CLIENT_HEARTBEAT_TIMEOUT, GRID_SIZE, MAX_RECV_SIZE, PACKET_LIFETIME
import logging

# configure client console logging so UI runs print client logs to the terminal
logging.basicConfig(level=logging.INFO, format='[CLIENT] %(message)s')
logger = logging.getLogger('gsyn.client')

SERVER_ADDR = (CLIENT_SERVER_HOST, CLIENT_SERVER_PORT)


class Client:
    def __init__(self, server_addr=SERVER_ADDR, heartbeat_interval=CLIENT_HEARTBEAT_INTERVAL, heartbeat_timeout=CLIENT_HEARTBEAT_TIMEOUT):
        self.server_addr = server_addr
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)

        self.running = False
        self.state = 'disconnected'  # 'connecting', 'connected', 'disconnected'

        self.seq = 1
        self.seq_lock = threading.Lock()

        self.last_heartbeat_ack = 0.0
        self.last_recv_time = 0.0
        # track last received seq to drop duplicates or replays
        self.last_seq_received = 0
        self.last_recv_timestamp_ms = 0
        # track last received snapshot_id to drop redundant snapshots
        self.last_snapshot_id = 0

        # ===== PING & PACKET LOSS TRACKING =====
        # track sent packets for ping measurement: seq -> timestamp (ms)
        self.sent_packets = {}
        self.sent_packets_lock = threading.Lock()
        # rolling ping stats (ms)
        self.ping_ms = 0.0
        self.ping_samples = []  # keep last 10 samples
        # heartbeat id counter and pending heartbeats (heartbeat_id -> timestamp_ms)
        self.heartbeat_id = 0
        self.heartbeat_lock = threading.Lock()
        self.pending_heartbeats = {}
        self.pending_heartbeats_lock = threading.Lock()
        # packet loss tracking: expect next seq from server
        self.expected_next_recv_seq = 1
        self.packets_lost = 0  # count of lost packets
        self.packets_received = 0  # count of received packets
        self.recv_stats_lock = threading.Lock()

        # Grid (configurable size)
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # action buffer (kept for completeness)
        self.actions = []
        logger.info(f'created client; server={self.server_addr} grid={GRID_SIZE}x{GRID_SIZE}')

    def _send(self, data):
        try:
            self.sock.sendto(data, self.server_addr)
            # track sent packet for ping measurement
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
        # send initial init
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

            # drop old/duplicate seqs
            if seq_num <= self.last_seq_received:
                logger.info(f'dropping packet seq={seq_num} <= last_seq={self.last_seq_received}')
                continue

            # drop stale packets
            now_ms = int(time.time() * 1000)
            if now_ms - timestamp_ms > int(PACKET_LIFETIME * 1000):
                logger.info(f'dropping packet seq={seq_num} stale by {now_ms - timestamp_ms}ms')
                continue

            # accept this packet and update last seen seq
            self.last_seq_received = seq_num
            self.last_recv_timestamp_ms = timestamp_ms

            # ===== PING & LOSS TRACKING =====
            # detect packet loss by checking for gaps in seq_num
            with self.recv_stats_lock:
                if seq_num > self.expected_next_recv_seq:
                    # gap detected: count missing packets as lost
                    gap = seq_num - self.expected_next_recv_seq
                    self.packets_lost += gap
                    logger.info(f'packet loss detected: gap of {gap} (expected {self.expected_next_recv_seq}, got {seq_num})')
                self.expected_next_recv_seq = seq_num + 1
                self.packets_received += 1

            # measure ping for two cases:
            # server ACKs a heartbeat by returning the same heartbeat_id
            now_ms = int(time.time() * 1000)

            # heartbeat ack (snapshot_id field contains heartbeat_id)
            

            if msg_type == MSG_ACK:
                # server acknowledged our INIT or ACK or heartbeat
                self.state = 'connected'
                self.last_heartbeat_ack = time.time()
                logger.info(f'ACK received seq={seq_num} snapshot(heartbeat_id)={snapshot_id}')
                hb_id = snapshot_id
                with self.pending_heartbeats_lock:
                     if hb_id in self.pending_heartbeats:
                        sent_time = self.pending_heartbeats.pop(hb_id)
                        ping = now_ms - sent_time
                        self.ping_samples.append(ping)
                        if len(self.ping_samples) > 10:
                            self.ping_samples.pop(0)
                        self.ping_ms = sum(self.ping_samples) / len(self.ping_samples)
                        logger.info(f'ping (heartbeat): {ping}ms (avg: {self.ping_ms:.1f}ms)')

            elif msg_type == MSG_SNAPSHOT:
                # drop redundant snapshots (same or older snapshot_id)
                if snapshot_id <= self.last_snapshot_id:
                    logger.info(f'dropping SNAPSHOT id={snapshot_id} <= last_id={self.last_snapshot_id}')
                    continue

                # update last snapshot_id
                self.last_snapshot_id = snapshot_id

                # parse payload: starts at offset 28
                payload_len = struct.unpack("!H", data[22:24])[0]
                payload = data[28:28+payload_len] if payload_len > 0 else b''
                if payload:
                    try:
                        count = struct.unpack("!H", payload[:2])[0]
                        offset = 2
                        for i in range(count):
                            if offset + 6 > len(payload):
                                break
                            row, col, player_id = struct.unpack("!H H H", payload[offset:offset+6])
                            offset += 6
                            if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                                self.grid[row][col] = player_id
                    except Exception:
                        pass

                logger.info(f'SNAPSHOT received id={snapshot_id} seq={seq_num} actions={count if payload else 0}')

                # if we are not currently connected, send ACK to request re-activation
                if self.state != 'connected':
                    self.send_ack()

            elif msg_type == MSG_HEARTBEAT:
                # reply with ACK
                self.last_heartbeat_ack = time.time()
                logger.info(f'HEARTBEAT received seq={seq_num} — sending ACK')
                self.send_ack()

    def _heartbeat_loop(self):
        while self.running:
            now = time.time()
            if self.state == 'connected':
                # send heartbeat
                with self.seq_lock:
                    s = self.seq
                    self.seq += 1
                # create a heartbeat id and send it in the snapshot_id field
                with self.heartbeat_lock:
                    self.heartbeat_id += 1
                    hb_id = self.heartbeat_id
                hb = pack_header(MSG_HEARTBEAT, hb_id, s, 0)
                # record pending heartbeat timestamp for ping measurement
                now_ms = int(time.time() * 1000)
                with self.pending_heartbeats_lock:
                    self.pending_heartbeats[hb_id] = now_ms
                self._send(hb)
                # check timeout
                if now - self.last_heartbeat_ack > self.heartbeat_timeout:
                    self.state = 'disconnected'
            else:
                # attempt to connect
                self.send_init()
            time.sleep(self.heartbeat_interval)


if __name__ == '__main__':
    # simple CLI run for manual testing
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

import socket
import struct
import threading
import time
from util import pack_header, MSG_INIT, MSG_ACTION, MSG_SNAPSHOT, MSG_ACK, MSG_HEARTBEAT, check_auth
from config import CLIENT_SERVER_HOST, CLIENT_SERVER_PORT, CLIENT_HEARTBEAT_INTERVAL, CLIENT_HEARTBEAT_TIMEOUT, GRID_SIZE, MAX_RECV_SIZE

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

        # Grid (configurable size)
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # action buffer (kept for completeness)
        self.actions = []

    def _send(self, data):
        try:
            self.sock.sendto(data, self.server_addr)
        except Exception:
            pass

    def send_init(self):
        with self.seq_lock:
            s = self.seq
            self.seq += 1
        header = pack_header(MSG_INIT, 0, s, 0)
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
        self._send(header + payload)

    def send_ack(self):
        with self.seq_lock:
            s = self.seq
            self.seq += 1
        header = pack_header(MSG_ACK, 0, s, 0)
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
                continue
            msg_type = data[5]
            snapshot_id = struct.unpack("!I", data[6:10])[0]
            seq_num = struct.unpack("!I", data[10:14])[0]

            if msg_type == MSG_ACK:
                # server acknowledged our INIT or ACK
                self.state = 'connected'
                self.last_heartbeat_ack = time.time()
                # print("[CLIENT] ACK received — connected")

            elif msg_type == MSG_SNAPSHOT:
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

                # if we are not currently connected, send ACK to request re-activation
                if self.state != 'connected':
                    self.send_ack()

            elif msg_type == MSG_HEARTBEAT:
                # reply with ACK
                self.last_heartbeat_ack = time.time()
                self.send_ack()

    def _heartbeat_loop(self):
        while self.running:
            now = time.time()
            if self.state == 'connected':
                # send heartbeat
                with self.seq_lock:
                    s = self.seq
                    self.seq += 1
                hb = pack_header(MSG_HEARTBEAT, 0, s, 0)
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

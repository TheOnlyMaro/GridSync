import struct
import time
import zlib

HEADER_FORMAT = "!4s B B I I Q H I"  # 28 bytes

MSG_INIT = 0
MSG_ACTION = 1
MSG_SNAPSHOT = 2
MSG_ACK = 3
MSG_HEARTBEAT = 4


def pack_header(msg_type, snapshot_id, seq_num, payload_len):
    protocol_id = b"GSYN"
    version = 1
    timestamp = int(time.time() * 1000)
    # pack with zero checksum, compute real checksum, then repack
    packed_zero = struct.pack(
        HEADER_FORMAT, protocol_id, version, msg_type,
        snapshot_id, seq_num, timestamp, payload_len, 0
    )
    checksum = generate_checksum(packed_zero)
    return struct.pack(
        HEADER_FORMAT, protocol_id, version, msg_type,
        snapshot_id, seq_num, timestamp, payload_len, checksum
    )


def pack_actions_payload(actions_list):
    """Pack actions into payload: 2-byte count, then tuples (row, col, player_id) each 2 bytes."""
    payload = struct.pack("!H", len(actions_list))
    for row, col, player_id in actions_list:
        payload += struct.pack("!H H H", row, col, player_id)
    return payload


def unpack_actions_payload(payload):
    """Unpack actions payload into list of (row,col,player_id)."""
    if not payload:
        return []
    try:
        count = struct.unpack("!H", payload[:2])[0]
    except Exception:
        return []
    res = []
    offset = 2
    for i in range(count):
        if offset + 6 > len(payload):
            break
        row, col, player_id = struct.unpack("!H H H", payload[offset:offset+6])
        res.append((row, col, player_id))
        offset += 6
    return res


def generate_checksum(header_bytes_without_checksum):
    """Generate a 32-bit CRC checksum for header bytes (checksum field should be zeroed).

    Expects the header bytes where the final 4 checksum bytes are zero.
    Returns an unsigned 32-bit int.
    """
    return zlib.crc32(header_bytes_without_checksum) & 0xFFFFFFFF


def check_auth(header_bytes):
    """Check that protocol id is 'GSYN' and the checksum matches.

    Returns (True, 'ok') on success or (False, reason) on failure.
    """
    hdr_len = struct.calcsize(HEADER_FORMAT)
    if len(header_bytes) < hdr_len:
        return False, "header too short"

    protocol_id = header_bytes[:4]
    if protocol_id != b"GSYN":
        return False, "invalid protocol id"

    # Zero out checksum bytes (last 4 bytes of header) and compute checksum
    zeroed = header_bytes[:hdr_len-4] + b"\x00\x00\x00\x00"
    computed = generate_checksum(zeroed)
    actual_checksum = struct.unpack("!I", header_bytes[hdr_len-4:hdr_len])[0]
    if computed != actual_checksum:
        return False, "checksum mismatch"

    return True, "ok"

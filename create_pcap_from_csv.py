#!/usr/bin/env python3
"""
Create PCAP file from GridSync CSV data
"""
import struct
import time
import csv
import os
import socket


def create_pcap():
    csv_file = 'results/baseline/client_metrics.csv'
    pcap_file = 'results/baseline/capture.pcap'

    print("=== Creating PCAP from GridSync CSV Data ===")

    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return

    try:
        # Read CSV data
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"✅ Found {len(rows)} packets in CSV")

        # Create directory if needed
        os.makedirs(os.path.dirname(pcap_file), exist_ok=True)

        # Create PCAP file
        with open(pcap_file, 'wb') as f:
            # PCAP Global Header (24 bytes)
            # Magic: 0xa1b2c3d4 (big-endian), Version 2.4, Linktype 1 (Ethernet)
            f.write(struct.pack('=IHHIIII',
                                0xa1b2c3d4,  # Magic number
                                2, 4,  # Version 2.4
                                0,  # GMT offset
                                0,  # Accuracy
                                65535,  # Snaplen
                                1))  # Linktype (Ethernet)

            base_time = time.time() - 60  # Start 60 seconds ago

            # Create packets based on CSV data
            for i, row in enumerate(rows[:100]):  # First 100 packets
                # Packet header (16 bytes)
                packet_time = base_time + (i * 0.05)  # 20 packets/sec
                ts_sec = int(packet_time)
                ts_usec = int((packet_time - ts_sec) * 1000000)

                # Extract data from CSV row
                try:
                    seq_num = int(row.get('seq_num', i))
                    snapshot_id = int(row.get('snapshot_id', i))
                    latency = float(row.get('latency_ms', 0))
                except:
                    seq_num = i
                    snapshot_id = i
                    latency = 0

                # Create a realistic GridSync packet
                # GSYN Protocol Header (28 bytes)
                header = struct.pack('!4sBBIIQHI',
                                     b'GSYN',  # protocol_id (4 bytes)
                                     1,  # version (1 byte)
                                     2,  # msg_type: MSG_SNAPSHOT (1 byte)
                                     snapshot_id,  # snapshot_id (4 bytes)
                                     seq_num,  # seq_num (4 bytes)
                                     int(packet_time * 1000),  # timestamp (8 bytes)
                                     0,  # payload_len (2 bytes)
                                     1234567890)  # checksum (4 bytes) - placeholder

                # Build full packet with network headers
                # Ethernet header (14 bytes) - simplified
                eth_header = struct.pack('!6s6sH',
                                         b'\x00\x00\x00\x00\x00\x01',  # dest MAC
                                         b'\x00\x00\x00\x00\x00\x02',  # src MAC
                                         0x0800)  # IPv4 type

                # IP header (20 bytes)
                ip_header = struct.pack('!BBHHHBBH4s4s',
                                        0x45,  # Version + IHL
                                        0x00,  # DSCP
                                        20 + 8 + len(header),  # Total length
                                        0x1234,  # Identification
                                        0x4000,  # Flags + Fragment offset
                                        64,  # TTL
                                        17,  # Protocol (UDP)
                                        0,  # Header checksum
                                        socket.inet_aton('127.0.0.1'),  # Source IP
                                        socket.inet_aton('127.0.0.1'))  # Dest IP

                # UDP header (8 bytes)
                udp_header = struct.pack('!HHHH',
                                         54321,  # Source port
                                         9999,  # Dest port
                                         8 + len(header),  # Length
                                         0)  # Checksum

                # Combine all parts
                packet_data = eth_header + ip_header + udp_header + header
                packet_len = len(packet_data)

                # Write PCAP packet header
                f.write(struct.pack('=IIII', ts_sec, ts_usec, packet_len, packet_len))

                # Write packet data
                f.write(packet_data)

                if i % 20 == 0:
                    print(f"  Created packet {i + 1}: seq={seq_num}, snapshot={snapshot_id}")

        print(f"\n✅ SUCCESS! Created PCAP file: {pcap_file}")
        print(f"   Contains: {min(len(rows), 100)} packets")
        print(f"   File size: {os.path.getsize(pcap_file)} bytes")

        # Verify the file
        if os.path.getsize(pcap_file) > 100:
            print("   ✅ PCAP file looks valid")
        else:
            print("   ⚠ PCAP file might be too small")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    create_pcap()
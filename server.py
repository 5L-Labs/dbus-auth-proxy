#!/usr/bin/python3

import socket
import os
import struct
import signal
import sys

ADDR = "./real.sock"
SO_PEERCRED = getattr(socket, "SO_PEERCRED", 17)

running = True


def graceful_shutdown(signum, frame):
    global running
    print(f"\n[SIGNAL {signum}] Shutting down gracefully...")
    running = False


signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

# Remove the socket file if it already exists to avoid "Address already in use"
if os.path.exists(ADDR):
    os.remove(ADDR)

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.bind(ADDR)
    s.listen(5)
    s.settimeout(1.0)
    print(f"Server is listening on {ADDR}...")

    while running:
        try:
            conn, addr = s.accept()
        except socket.timeout:
            continue  # Check 'running' flag again
        with conn:
            creds = conn.getsockopt(
                socket.SOL_SOCKET, SO_PEERCRED, struct.calcsize("3i")
            )
            pid, uid, gid = struct.unpack("3i", creds)

            print(f"\n[CREDENTIAL CHECK]")
            print(f"  Peer PID: {pid}")
            print(f"  Peer UID: {uid}")
            print(f"  Peer GID: {gid}")

            data = conn.recv(1024)
            if not data:
                break
            print(f"Server received: {data.decode()}")
            conn.sendall(b"ACK: Hello from Server")

if os.path.exists(ADDR):
    os.remove(ADDR)

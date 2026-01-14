#!/usr/bin/python3

import socket
import threading
import os
from enum import Enum, auto

# --- CONFIGURATION ---
# The path where this proxy will listen for incoming connections
LISTEN_PATH = "sockets/upstream_socket"
# The path where the actual service is listening
TARGET_PATH = "sockets/system_bus_socket"

SOURCE_UID = 0
REPLACEMENT_UID_HEX = str(os.getuid()).encode("ascii").hex().encode()
SOURCE_UID_HEX = str(SOURCE_UID).encode("ascii").hex().encode()


class Direction(Enum):
    TO_DBUS = auto()
    TO_CLIENT = auto()


def transform_data(data):
    """
    Modify data here.
    direction: 'to_target' or 'to_client'
    """
    # Example: Append a timestamp or modify bytes
    if data.startswith(b"\x00AUTH EXTERNAL"):
        data = data.replace(
            b"AUTH EXTERNAL " + SOURCE_UID_HEX + b"\r\n",
            b"AUTH EXTERNAL " + REPLACEMENT_UID_HEX + b"\r\n",
        )
    return data


def forward(source, destination, direction):
    transform_auth = direction == Direction.TO_DBUS
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break

            if transform_auth:
                data = transform_data(data)
                transform_auth = False
            destination.sendall(data)
    except Exception as e:
        pass
    finally:
        source.close()
        destination.close()


def start_unix_proxy():
    if os.path.exists(LISTEN_PATH):
        os.remove(LISTEN_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(LISTEN_PATH)
    server.listen(5)

    os.chmod(LISTEN_PATH, 0o777)

    print(f"[*] Proxy listening on {LISTEN_PATH}")
    print(f"[*] Forwarding to {TARGET_PATH}")

    try:
        while True:
            client_sock, _ = server.accept()

            # 3. Connect to the target UNIX socket
            try:
                target_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                target_sock.connect(TARGET_PATH)
            except Exception as e:
                print(f"[!] Could not connect to target: {e}")
                client_sock.close()
                continue

            # 4. Start bidirectional forwarding
            threading.Thread(
                target=forward,
                args=(client_sock, target_sock, Direction.TO_DBUS),
                daemon=True,
            ).start()
            threading.Thread(
                target=forward,
                args=(target_sock, client_sock, Direction.TO_CLIENT),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down.")
    finally:
        if os.path.exists(LISTEN_PATH):
            os.remove(LISTEN_PATH)


if __name__ == "__main__":
    start_unix_proxy()

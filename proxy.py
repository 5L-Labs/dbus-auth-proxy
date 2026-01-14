#!/usr/bin/python3

from enum import Enum, auto
from socket import socket

import argparse
import re
import os
import threading

SOCKET_BACKLOG = 50
DEFAULT_BUFFER = 4096
REPLACEMENT_UID_HEX = str(os.getuid()).encode("ascii").hex().encode()


class Direction(Enum):
    TO_DBUS = auto()
    TO_CLIENT = auto()


def transform_uid(data: bytes) -> bytes:
    """
    Replaces the UID for a AUTH EXTERNAL command to the current user's UID
    if and only if UID was originally provided.

    Args:
        data (bytes): The data from the socket for the AUTH statement

    Returns:
        bytes: The data with the UID replaced.
    """
    return re.sub(
        b"\x00AUTH EXTERNAL \\d+",
        b"\x00AUTH EXTERNAL " + REPLACEMENT_UID_HEX,
        data,
    )


def forward(source: socket, destination: socket, direction: Direction) -> None:
    """
    Forwards data from source socket to destination socket while replacing AUTH
    EXTERNAL UIDs.

    Replacement only happens for the first dbus command going from client to
    dbus. All other data is forwarded blindly.

    Args:
        source(socket): The source socket
        destination(socket): The destination socket
        direction(Direction): If we're forwarding to or from dbus
    """
    transform_auth = direction == Direction.TO_DBUS
    try:
        while True:
            data = source.recv(DEFAULT_BUFFER)
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


def start_dbus_proxy(client: str, dbus: str, buffer_size: int) -> None:
    """
    Starts the dbus proxy.

    This will forward traffic from the client to dbus, while overriding UID for
    EXTERNAL AUTH if provided to the current running user's UID.

    If will also forward the reverse but with no overrides.

    Args:
        client (str): The path to the socket dbus clients connect to.
        dbus (str): The path to the dbus client to forward traffic to.
        buffer_size (int): The buffer size used for the transfer
    """
    if os.path.exists(client):
        os.remove(client)

    server = socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(dbus)
    server.listen(SOCKET_BACKLOG)

    print(f"[*] Proxy listening on {client}")
    print(f"[*] Forwarding to {dbus}")

    try:
        while True:
            client_sock, _ = server.accept()

            try:
                target_sock = socket(socket.AF_UNIX, socket.SOCK_STREAM)
                target_sock.connect(dbus)
            except Exception as e:
                print(f"[!] Could not connect to target: {e}")
                client_sock.close()
                continue

            threading.Thread(
                target=forward,
                args=(
                    client_sock,
                    target_sock,
                    Direction.TO_DBUS,
                    buffer_size,
                ),
            ).start()
            threading.Thread(
                target=forward,
                args=(
                    client_sock,
                    target_sock,
                    Direction.TO_DBUS,
                    buffer_size,
                ),
            ).start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down.")
    finally:
        if os.path.exists(client):
            os.remove(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        A dbus proxy that overwrites AUTH EXTERNAL commands's UID to current UID.

        UIDs will only be overwritten if they are provided.
        """,
    )

    parser.add_argument(
        "client_socket",
        help="""
        The path to the socket the dbus client connects to, will be created
        """,
    )

    parser.add_argument(
        "system_dbus",
        help="""
        The socket for the system dbus. Normally /run/dbus/system_bus_socket
        for system dbus.
        """,
    )

    parser.add_argument(
        "-b",
        "--buffer_size",
        default=DEFAULT_BUFFER,
        help="""
        The buffer size used for forwarding
        """,
    )

    args = parser.parse_args()

    start_unix_proxy(args.client_socket, args.system_dbus, args.buffer_size)

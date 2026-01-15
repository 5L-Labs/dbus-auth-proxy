#!/usr/bin/python3

from typing import Callable, Optional

from socket import SO_PEERCRED, SOL_SOCKET
from asyncio import StreamReader, StreamWriter

import argparse
import asyncio
import struct
import os
import re

DEFAULT_BUFFER = 4096
PROCESS_UID = os.getuid()
REPLACEMENT_UID_HEX = str(PROCESS_UID).encode("ascii").hex().encode()


def get_socket_uid(writer: StreamWriter) -> Optional[int]:
    sock = writer.get_extra_info("socket")
    if sock is None:
        return None

    try:
        peercred_bytes = sock.getsockopt(
            SOL_SOCKET, SO_PEERCRED, struct.calcsize("3i")
        )
        _, uid, _ = struct.unpack("3i", peercred_bytes)
        return uid
    except (OSError, struct.error) as e:
        print(f"Could not get peer credentials: {e}")
        return None


def verify_and_transform(data: bytes, socket_uid: int) -> bytes:
    if socket_uid != PROCESS_UID:
        raise PermissionError(
            f"Client is not root and Client UID ({socket_uid}) != Proxy UID ({PROCESS_UID})"
        )

    return re.sub(
        b"\x00AUTH EXTERNAL \\d+",
        b"\x00AUTH EXTERNAL " + REPLACEMENT_UID_HEX,
        data,
    )


async def forward(
    from_stream: StreamReader, to_stream: StreamWriter, buffer_size: int
) -> None:
    while not from_stream.at_eof():
        data = await from_stream.read(buffer_size)
        if not data:
            break
        to_stream.write(data)
        await to_stream.drain()

    await to_stream.drain()


async def run_proxy(
    auth_data: bytes,
    upstream_reader: StreamReader,
    upstream_writer: StreamWriter,
    dbus_soc: str,
    buffer_size: int,
) -> None:
    (downstream_reader, downstream_writer) = (
        await asyncio.open_unix_connection(path=dbus_soc)
    )

    downstream_writer.write(auth_data)
    await downstream_writer.drain()

    dbus_to_client = asyncio.create_task(
        forward(downstream_reader, upstream_writer, buffer_size)
    )
    client_to_dbus = asyncio.create_task(
        forward(upstream_reader, downstream_writer, buffer_size)
    )

    await asyncio.wait(
        {dbus_to_client, client_to_dbus}, return_when=asyncio.FIRST_COMPLETED
    )

    downstream_writer.close()
    await downstream_writer.wait_closed()


async def client_callback(
    reader: StreamReader, writer: StreamWriter, dbus_soc: str, buffer_size: int
) -> None:
    socket_uid = get_socket_uid(writer)
    if socket_uid is None:
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        return

    try:
        auth_data = await reader.readline()
        auth_data = verify_and_transform(auth_data, socket_uid)

        await run_proxy(auth_data, reader, writer, dbus_soc, buffer_size)
    except PermissionError as e:
        print(f"[*] Permission Denied: {e}")
    finally:
        await writer.drain()
        writer.close()
        await writer.wait_closed()


def gen_client_callback(
    dbus_soc: str, buffer_size: int
) -> Callable[[StreamReader, StreamWriter], Awaitable[None]]:
    async def callback(reader: StreamReader, writer: StreamWriter) -> None:
        await client_callback(reader, writer, dbus_soc, buffer_size)

    return callback


def parse_args() -> argparse.Namespace:
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

    return parser.parse_args()


async def main(args: argparse.Namespace) -> None:
    args = parse_args()

    if os.path.exists(args.client_socket):
        os.remove(args.client_socket)

    handle_client = gen_client_callback(args.system_dbus, args.buffer_size)
    server = await asyncio.start_unix_server(
        handle_client, path=args.client_socket
    )

    print(f"[*] Proxy listening on {args.client_socket}")
    print(f"[*] Forwarding to {args.system_dbus}")

    await server.serve_forever()


if __name__ == "__main__":
    args = parse_args()
    try:
        if os.path.exists(args.client_socket):
            os.remove(args.client_socket)
        asyncio.run(main(args))
    except KeyboardInterrupt as e:
        print("[*] Shutting Down")
    finally:
        if os.path.exists(args.client_socket):
            os.remove(args.client_socket)

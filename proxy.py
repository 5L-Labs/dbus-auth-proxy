#!/usr/bin/python3

from typing import Callable, Optional

from socket import SO_PEERCRED, SOL_SOCKET
from asyncio import StreamReader, StreamWriter

import asyncio
import struct
import os
import re

from opts import Options, get_opts

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


async def handle_client(
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

        await handle_client(auth_data, reader, writer, dbus_soc, buffer_size)
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


async def run_proxy(opts: Options) -> None:
    if os.path.exists(opts.client_socket):
        os.remove(opts.client_socket)

    handle_client = gen_client_callback(opts.system_dbus, opts.buffer_size)
    server = await asyncio.start_unix_server(
        handle_client, path=opts.client_socket
    )

    print(f"[*] Proxy listening on {opts.client_socket}")
    print(f"[*] Forwarding to {opts.system_dbus}")

    await server.serve_forever()


if __name__ == "__main__":
    opts = get_opts()
    try:
        if os.path.exists(opts.client_socket):
            os.remove(opts.client_socket)
        asyncio.run(run_proxy(opts))
    except KeyboardInterrupt as e:
        print("[*] Shutting Down")
    finally:
        if os.path.exists(opts.client_socket):
            os.remove(opts.client_socket)

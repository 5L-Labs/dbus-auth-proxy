"""
Module for options for the proxy.

Options are set up with environment variables. This makes it simpler to feed
into as a containerized app.

Functions:
  - get_opts(): Gets the options
"""

import os

BUFFER_ENV = "BUFFER_SIZE"
BUFFER_DEF = "4096"

CLIENT_SOCK_ENV = "CLIENT_SOCKET"
CLIENT_SOCK_DEF = "/run/dbus-auth-proxy/system_bus_socket"

DBUS_SOCK_ENV = "SYSTEM_DBUS"
DBUS_SOCK_DEF = "/run/dbus/system_bus_socket"


class Options:
    """
    Options for the auth proxy.

    Attributes
    ----------
    buffer_size : int
        Buffer size in bytes used to ferry data across the two sockets.
    client_socket : str
        Path to the socket client will connnect to.
    system_dbus : str
        Path to the system dbus to forward data to.
    """

    buffer_size: int
    client_socket: str
    system_dbus: str


def get_opts() -> Options:
    """
    Generates the options for the auth proxy

    Returns:
        Options: options for the proxy
    """
    options = Options()

    options.buffer_size = int(os.environ.get(BUFFER_ENV, BUFFER_DEF))
    options.client_socket = os.environ.get(CLIENT_SOCK_ENV, CLIENT_SOCK_DEF)
    options.system_dbus = os.environ.get(DBUS_SOCK_ENV, DBUS_SOCK_DEF)

    return options

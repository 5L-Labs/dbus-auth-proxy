import os

BUFFER_ENV = "BUFFER_SIZE"
BUFFER_DEF = "4096"

CLIENT_SOCK_ENV = "CLIENT_SOCKET"
CLIENT_SOCK_DEF = "/run/dbus-auth-proxy/system_bus_socket"

DBUS_SOCK_ENV = "SYSTEM_DBUS"
DBUS_SOCK_DEF = "/run/dbus/system_bus_socket"


class Options:
    buffer_size: int
    client_socket: str
    system_dbus: str


def get_opts() -> Options:
    options = Options()

    options.buffer_size = int(os.environ.get(BUFFER_ENV, BUFFER_DEF))
    options.client_socket = os.environ.get(CLIENT_SOCK_ENV, CLIENT_SOCK_DEF)
    options.system_dbus = os.environ.get(DBUS_SOCK_ENV, DBUS_SOCK_DEF)

    return options

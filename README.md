# dbus-auth-proxy

dbus-auth-proxy is a proxy that overrides the user id in the [AUTH EXTERNAL](https://dbus.freedesktop.org/doc/dbus-specification.html#auth-mechanisms-external) message of a dbus request. The proxy is intended to be used in containers running in rootless mode (e.g. podman rootless containers) to access the system dbus when the application's dbus client sets a UID in AUTH EXTERNAL.

It produces a unix socket that mimics the system dbus unix socket. This socket should then be mounted in the rootless container in question at `/run/dbus/system_bus_socket` so that dbus requests flow through the proxy and their AUTH EXTERNAL message will be fixed.

## License

See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).

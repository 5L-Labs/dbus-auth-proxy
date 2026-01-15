FROM python:slim

WORKDIR /proxy

COPY proxy.py .

CMD ["python3", "proxy.py", "/run/dbus-auth-proxy/system_bus_socket", "/run/dbus/system_bus_socket"]

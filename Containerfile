FROM python:slim

WORKDIR /proxy

COPY src/proxy.py .
COPY src/opts.py .

ENV BUFFER_SIZE 4096
ENV CLIENT_SOCKET /run/dbus-auth-proxy/system_bus_socket
ENV SYSTEM_DBUS /run/dbus/system_bus_socket

CMD ["python3", "proxy.py"]

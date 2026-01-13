# Use a lightweight Python base image
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Copy the client script into the container
COPY client.py .

RUN apk update && apk add dbus --no-cache

# Command to run the client
# CMD ["python3", "client.py"]

# Command for DBUS
CMD ["dbus-send", "--bus=unix:path=./proxy.sock", "--print-reply", "--dest=org.freedesktop.systemd1", "/org/freedesktop/systemd1", "org.freedesktop.DBus.Introspectable.Introspect"]

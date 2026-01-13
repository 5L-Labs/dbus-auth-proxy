#!/usr/bin/python3

import socket

# Connect to the SOCAT proxy, not the real server
PROXY_ADDR = "./proxy.sock"

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect(PROXY_ADDR)
    print(f"Client connected to {PROXY_ADDR}")
    s.sendall(b"Hello World through the proxy!")
    response = s.recv(1024)
    print(f"Client received response: {response.decode()}")

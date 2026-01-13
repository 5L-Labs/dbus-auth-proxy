#!/bin/bash

socat -v UNIX-LISTEN:./proxy.sock,fork UNIX-CONNECT:./real.sock

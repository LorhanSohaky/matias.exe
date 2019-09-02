#!/usr/bin/python3
import socket, base64, os
def recvline(s):
    buf = b''
    while True:
        c = s.recv(1)
        buf += c
        if c == b'' or c == b'\n':
            return buf
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 7000))
for i in range(16):
    msg = base64.b32encode(os.urandom(512))
    s.send(msg + b'\n')
    assert recvline(s) == b'/error\n'
s.close()


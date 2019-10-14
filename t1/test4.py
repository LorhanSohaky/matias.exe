#!/usr/bin/env python3
import socket, base64, os
def myrand(n=512):
    return base64.b32encode(os.urandom(n))
def recvline(s):
    buf = b''
    while True:
        c = s.recv(1)
        buf += c
        if c == b'' or c == b'\n':
            #print('recvline', s.fileno(), buf)
            return buf

s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s1.connect(('localhost', 7000))
s1.send(myrand()+b'\n')
assert recvline(s1) == b'/error\n'
n1 = myrand(12)
s1.send(b'/nick %s\n' % n1)
assert recvline(s1) == b'/joined %s\n'%n1

s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s2.connect(('localhost', 7000))
n2 = myrand(8)
s2.send(b'/nick %s\n' % n2)
assert recvline(s1) == b'/joined %s\n'%n2
assert recvline(s2) == b'/joined %s\n'%n2
s2.send(b'/nick %s\n' % n1)
assert recvline(s2) == b'/error\n'

msg = myrand()
s2.send(msg+b'\n')
assert recvline(s1) == b'%s: %s\n' % (n2, msg)
assert recvline(s2) == b'%s: %s\n' % (n2, msg)

msg = myrand()
s1.send(msg+b'\n')
assert recvline(s1) == b'%s: %s\n' % (n1, msg)
assert recvline(s2) == b'%s: %s\n' % (n1, msg)

oldn2 = n2
n2 = myrand(9)
s2.send(b'/nick %s\n' % n2)
assert recvline(s1) == b'/renamed %s %s\n'%(oldn2, n2)
assert recvline(s2) == b'/renamed %s %s\n'%(oldn2, n2)

msg = myrand()
s2.send(msg+b'\n')
assert recvline(s1) == b'%s: %s\n' % (n2, msg)
assert recvline(s2) == b'%s: %s\n' % (n2, msg)

s3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s3.connect(('localhost', 7000))
s3.send(myrand()+b'\n')
assert recvline(s3) == b'/error\n'
s3.close()

s3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s3.connect(('localhost', 7000))
s3.close()

s2.close()

assert recvline(s1) == b'/quit %s\n'%n2

s1.close()

#!/usr/bin/python3
import socket, select, base64, os
def recvline(s):
    buf = b''
    while True:
        c = s.recv(1)
        buf += c
        if c == b'' or c == b'\n':
            return buf
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 7000))
def myrand(n=512):
    return base64.b32encode(os.urandom(n))

s.send(myrand(200))
r,_,_=select.select([s],[],[],0.5)
assert r==[], 'O servidor não deveria responder enquanto não chegar uma linha inteira'

s.send(myrand(200) + b'\n')
assert recvline(s) == b'/error\n'

nick = myrand(8)
s.send(b'/nick %s\n' % nick)
assert recvline(s) == b'/joined %s\n' % nick

msg = myrand()
s.send(msg + b'\n')
assert recvline(s) == b'%s: %s\n' % (nick, msg)

oldnick = nick
nick = myrand(8)
s.send(b'/nick %s\n' % nick)
assert recvline(s) == b'/renamed %s %s\n' % (oldnick, nick)

msg = myrand()
s.send(msg + b'\n')
assert recvline(s) == b'%s: %s\n' % (nick, msg)

msg = myrand()
s.send(msg + b'\n')
assert recvline(s) == b'%s: %s\n' % (nick, msg)

s.close()

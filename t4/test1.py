#!/usr/bin/env python3
import random
from myslip import CamadaEnlace

class LinhaSerial:
    def __init__(self):
        self.callback = None
        self.fila = b''
    def registrar_recebedor(self, callback):
        self.callback = callback
    def enviar(self, dados):
        self.fila += dados

def rand_ip():
    return '%d.%d.%d.%d'%tuple(random.randint(1, 255) for i in range(4))

next_hop = rand_ip()
linha_serial = LinhaSerial()
enlace = CamadaEnlace({next_hop: linha_serial})

def caso(datagrama):
    enlace.enviar(datagrama, next_hop)
    assert linha_serial.fila == b'\xc0' + datagrama + b'\xc0', 'O início e o fim do quadro devem ser delimitados com o byte 0xC0'
    linha_serial.fila = b''

caso(b'\x01')
caso(b'\x00\x01')
caso(b'ABCDEF')
caso(b'\x10\x20\x30\x40\x50')
caso(128*b' ')
caso(1024*b' ')
caso(1500*b' ')

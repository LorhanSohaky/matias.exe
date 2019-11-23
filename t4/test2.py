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

def caso(datagrama, withescape):
    enlace.enviar(datagrama, next_hop)
    assert linha_serial.fila == b'\xc0' + withescape + b'\xc0', '%r deveria ter se tornado %r com as sequências de escape'%(datagrama, withescape)
    linha_serial.fila = b''

caso(b'\xc0', b'\xdb\xdc')
caso(b'A\xc0', b'A\xdb\xdc')
caso(b'\xc0B', b'\xdb\xdcB')
caso(b'C\xc0D', b'C\xdb\xdcD')
caso(b'\xdb', b'\xdb\xdd')
caso(b'$\xdb', b'$\xdb\xdd')
caso(b'\xdba', b'\xdb\xdda')
caso(b'T\xdbk', b'T\xdb\xddk')
caso(b'\xdb\xc0', b'\xdb\xdd\xdb\xdc')
caso(b'\xc0\xdb', b'\xdb\xdc\xdb\xdd')
caso(b'\xdb|\xc0', b'\xdb\xdd|\xdb\xdc')
caso(b'\xc0|\xdb', b'\xdb\xdc|\xdb\xdd')
caso(b'3K@\xdb4lK\xc0lM', b'3K@\xdb\xdd4lK\xdb\xdclM')
caso(b'L1\xc0llk\xdba', b'L1\xdb\xdcllk\xdb\xdda')

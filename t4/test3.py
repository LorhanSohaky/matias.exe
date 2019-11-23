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
datagramas = []
def recebedor(datagrama):
    datagramas.append(datagrama)
enlace.registrar_recebedor(recebedor)

def caso(entrada, saida):
    for datum in entrada:
        linha_serial.callback(datum)
    assert datagramas == saida, 'Ao receber os dados %r pela linha serial, deveriam ter sido reconhecidos os datagramas %r, mas foram reconhecidos %r' % (entrada,saida,datagramas)
    datagramas.clear()

# Casos de teste com um único quadro
caso([b'ABC\xc0'], [b'ABC'])      # o padrão exige que você saiba reconhecer se o 0xC0 estiver só no final
caso([b'\xc0ABC\xc0'], [b'ABC'])  # ou se estiver no final e no começo
caso([b'ABC\xc0'], [b'ABC'])      # e isso não deve afetar o reconhecimento de quadros subsequentes

# Casos de teste com um único quadro quebrado em pedaços
caso([b'\xc0ABC', b'\xc0'], [b'ABC'])
caso([b'A', b'BC', b'\xc0'], [b'ABC'])
caso([b'\xc0', b'A', b'BC\xc0'], [b'ABC'])
caso([b'\xc0', b'A', b'BC\xc0'], [b'ABC'])

# Casos de teste com mais de um quadro
caso([b'ABC\xc0DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0ABC\xc0DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0ABC\xc0\xc0DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0ABC\xc0\xc0DE\xc0\xc0FGHIJ\xc0'], [b'ABC', b'DE', b'FGHIJ'])

# Casos de teste com mais de um quadro, quebrados em pedaços
caso([b'A',b'BC',b'\xc0DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0AB',b'C\xc0',b'DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0',b'ABC',b'\xc0',b'\xc0',b'D',b'E',b'\xc0'], [b'ABC', b'DE'])
caso([b'\xc0',b'ABC\xc0\xc0',b'DE\xc0',b'\xc0FGHIJ',b'\xc0'], [b'ABC', b'DE', b'FGHIJ'])

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
caso([b'\xdb\xdd\xc0'], [b'\xdb'])
caso([b'\xc0\xdb\xdd\xc0'], [b'\xdb'])
caso([b'\xdb\xdd\xc0'], [b'\xdb'])
caso([b'\xdb\xdc\xc0'], [b'\xc0'])
caso([b'\xc0\xdb\xdc\xc0'], [b'\xc0'])
caso([b'\xdb\xdc\xc0'], [b'\xc0'])

caso([b'A\xdb\xdd\xc0'], [b'A\xdb'])
caso([b'\xc0\xdb\xddB\xc0'], [b'\xdbB'])
caso([b'CD\xdb\xdd\xc0'], [b'CD\xdb'])
caso([b'EF\xdb\xdcGHI\xc0'], [b'EF\xc0GHI'])
caso([b'\xc0JKL\xdb\xdc\xc0'], [b'JKL\xc0'])
caso([b'\xdb\xdcMNOP\xc0'], [b'\xc0MNOP'])

# Casos de teste com um único quadro quebrado em pedaços
caso([b'\xc0\xdb', b'\xdd\xc0'], [b'\xdb'])
caso([b'\xc0', b'\xdb', b'\xdd', b'\xc0'], [b'\xdb'])
caso([b'\xc0\xdb', b'\xdc\xc0'], [b'\xc0'])
caso([b'\xc0', b'\xdb', b'\xdc', b'\xc0'], [b'\xc0'])

caso([b'\xc0A\xdb', b'\xddB\xc0'], [b'A\xdbB'])
caso([b'\xc0C', b'D\xdb', b'\xddF', b'\xc0'], [b'CD\xdbF'])
caso([b'\xc0G\xdb', b'\xdcHI\xc0'], [b'G\xc0HI'])
caso([b'\xc0', b'\xdb', b'\xdcJ', b'\xc0'], [b'\xc0J'])

# Casos de teste com mais de um quadro
caso([b'ABC\xc0DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0ABC\xc0DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0ABC\xc0\xc0DE\xc0'], [b'ABC', b'DE'])
caso([b'\xc0ABC\xc0\xc0DE\xc0\xc0FGHIJ\xc0'], [b'ABC', b'DE', b'FGHIJ'])

# Casos de teste com mais de um quadro, quebrados em pedaços
caso([b'A',b'B\xdb\xddC',b'\xc0DE\xc0'], [b'AB\xdbC', b'DE'])
caso([b'\xc0AB',b'C\xc0\xdb\xdd',b'DE\xc0'], [b'ABC', b'\xdbDE'])
caso([b'\xc0\xdb\xdc',b'ABC',b'\xc0',b'\xc0',b'D',b'E',b'\xc0'], [b'\xc0ABC', b'DE'])
caso([b'\xc0',b'ABC\xc0\xc0',b'DE\xc0',b'\xc0F\xdb\xdcGHIJ',b'\xc0'], [b'ABC', b'DE', b'F\xc0GHIJ'])

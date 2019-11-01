#!/usr/bin/env python3
import random
from myiputils import *
from myip import CamadaRede

class CamadaEnlace:
    def __init__(self):
        self.callback = None
        self.fila = []
    def registrar_recebedor(self, callback):
        self.callback = callback
    def enviar(self, datagrama, next_hop):
        self.fila.append((datagrama, next_hop))

def rand_ip():
    return '%d.%d.%d.%d'%tuple(random.randint(1, 255) for i in range(4))

enlace = CamadaEnlace()
rede = CamadaRede(enlace)

def enviar_datagrama(dest):
    datagrama = b'E\x00\x00\x14\x00\x00\x00\x00@\x06\x00\x00\x01\x02\x03\x04' + str2addr(dest)
    assert len(datagrama) == 20
    enlace.callback(datagrama[:-10] + struct.pack('!H',calc_checksum(datagrama)) + datagrama[-8:])
    assert len(enlace.fila) == 1, 'Só foi recebido um datagrama, mas foi encaminhado mais de um'
    datagrama, next_hop = enlace.fila.pop()
    assert len(datagrama) == 20, 'O tamanho mudou ao ser encaminhado'
    dscp, ecn, identification, flags, frag_offset, ttl, proto, \
           src_addr, dst_addr, payload = read_ipv4_header(datagrama, verify_checksum=True)
    assert dscp == 0 and ecn == 0 and identification == 0 and flags == 0 and frag_offset == 0 and \
           ttl in {63, 64} and proto == IPPROTO_TCP and src_addr=='1.2.3.4' and dst_addr==dest and \
           len(payload) == 0, 'Foram alteradas informações do datagrama original'
    return next_hop

# Testa roteador com uma única rota padrão
gw = rand_ip()
rede.definir_tabela_encaminhamento([
    ('0.0.0.0/0', gw),
])
for i in range(16):
    next_hop = enviar_datagrama(rand_ip())
    assert next_hop == gw, 'Datagrama encaminhado para next_hop incorreto'

# Testa máscaras /1
for i in range(16):
    gw1 = rand_ip()
    gw2 = rand_ip()
    rede.definir_tabela_encaminhamento([
        (  '0.0.0.0/1', gw1),
        ('128.0.0.0/1', gw2),
    ])
    dest = rand_ip()
    next_hop = enviar_datagrama(dest)
    first_bit = int(dest.split('.')[0])>>7
    if first_bit == 0:
        assert next_hop == gw1, 'Datagrama encaminhado para next_hop incorreto'
    else:
        assert next_hop == gw2, 'Datagrama encaminhado para next_hop incorreto'

# Testa máscaras variadas
for j in range(8):
    gw1, gw2, gw3, gw4, gw5, gw6, gw7, gw8, gw9, gw10 = \
        tuple(rand_ip() for i in range(10))
    tbl = [
        ('200.0.0.0/8', gw1),
        ('201.0.0.0/8', gw2),
        ('202.0.0.0/9', gw3),
        ('202.128.0.0/9', gw4),
        ('203.98.0.0/18', gw5),
        ('203.98.192.0/18', gw6),
        ('204.54.91.0/27', gw7),
        ('204.54.91.160/27', gw8),
        ('1.2.3.4/32', gw9),
        ('5.6.7.8/32', gw10),
    ]
    dic = {gw:cidr for cidr,gw in tbl}
    random.shuffle(tbl)
    rede.definir_tabela_encaminhamento(tbl)
    a,b,c = tuple(random.randint(0, 255) for i in range(3))
    tests = [
        ('200.%d.%d.%d'%(a,b,c), gw1),
        ('201.%d.%d.%d'%(a,b,c), gw2),
        ('202.%d.%d.%d'%(a&~128,b,c), gw3),
        ('202.%d.%d.%d'%(a|128,b,c), gw4),
        ('203.98.%d.%d'%(a&~192,b), gw5),
        ('203.98.%d.%d'%(a|192,b), gw6),
        ('204.54.91.%d'%(a>>3), gw7),
        ('204.54.91.%d'%(160|(a>>3)), gw8),
        ('204.54.91.%d'%(192|(a>>3)), None),
        ('204.54.91.%d'%(64|(a>>3)), None),
        ('204.54.91.%d'%(128|(a>>3)), None),
        ('1.2.3.4', gw9),
        ('5.6.7.8', gw10),
        ('9.10.11.12', None),
    ]
    random.shuffle(tests)
    for dest, gw in tests:
        got_gw = enviar_datagrama(dest)
        assert got_gw == gw, \
               'Datagrama destinado a %s deveria ter casado com %s mas casou com %s' % \
               (dest, gw and dic[gw], got_gw and dic[got_gw])

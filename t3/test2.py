#!/usr/bin/env python3
import random
import os
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
myip = rand_ip()
rede.definir_endereco_host(myip)
rede.definir_tabela_encaminhamento([
    ('0.0.0.0/0', gw),
])
used_ids = set()
for i in range(64):
    dest = rand_ip()
    segmento = os.urandom(random.randint(0, 1024))
    rede.enviar(segmento, dest)
    assert len(enlace.fila) == 1, 'Só foi enviado um datagrama, mas foi encaminhado mais de um'
    datagrama, next_hop = enlace.fila.pop()
    assert len(datagrama) == 20 + len(segmento), 'Datagrama com tamanho %d em vez de %d. Será que você inseriu um cabeçalho fora do tamanho padrão de 20 bytes?' % (len(datagrama), 20 + len(segmento))
    dscp, ecn, identification, flags, frag_offset, ttl, proto, \
           src_addr, dst_addr, payload = read_ipv4_header(datagrama, verify_checksum=True)
    assert dscp==0 and ecn==0 and flags==0 and frag_offset==0, 'Os campos dscp, ecn, flags, flags_frag deveriam estar preenchidos com os valores padrão (zero)'
    assert ttl>=15, 'O seu TTL de %d é muito baixo. Recomendamos usar o padrão do Linux, que é 64.' % ttl
    assert proto==IPPROTO_TCP, 'Você deve assumir que o protocolo de camada superior é o TCP'
    assert src_addr==myip, 'Produza datagramas com meu_endereco como remetente'
    assert dst_addr==dest, 'Pedimos para enviar para o destino %s, mas foi enviado para %s' % (dest, dst_addr)
    assert payload==segmento, 'O payload não bate com o segmento que pedimos para enviar'
    assert next_hop==gw, 'O datagrama deveria ter sido encaminhado via %s, mas foi encaminhado via %s' % (gw, next_hop)

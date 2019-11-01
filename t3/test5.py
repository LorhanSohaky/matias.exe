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

def enviar_datagrama(dest, ttl, gw, myip):
    datagrama = b'E\x00\x00\x14\x00\x00\x00\x00'+bytes([ttl])+b'\x06\x00\x00\x01\x02\x03\x04' + str2addr(dest)
    assert len(datagrama) == 20
    datagrama = datagrama[:-10] + struct.pack('!H',calc_checksum(datagrama)) + datagrama[-8:]
    enlace.callback(datagrama)
    if ttl == 1:
        assert len(enlace.fila) == 1, 'Deveria ter vindo um erro ICMP ao descartar o pacote'
        # Assegura que é um erro ICMP
        datagrama_, next_hop = enlace.fila.pop()
        dscp, ecn, identification, flags, frag_offset, ttl_, proto, \
               src_addr, dst_addr, payload = read_ipv4_header(datagrama_, verify_checksum=True)
        assert proto == IPPROTO_ICMP, 'O datagrama deveria ter sido descartado, a única coisa que poderia ter sido mandada era um erro ICMP'
        assert dst_addr == '1.2.3.4', 'Endereço de destino %r incorreto' % dst_addr
        assert src_addr == myip, 'Endereço de destino %r incorreto, deveria ser %r' % (src_addr, myip)
        assert dscp==0 and ecn==0 and flags==0 and frag_offset==0, 'Os campos dscp, ecn, flags, flags_frag deveriam estar preenchidos com os valores padrão (zero)'
        assert ttl_>=15, 'O seu TTL de %d é muito baixo. Recomendamos usar o padrão do Linux, que é 64.' % ttl_
        assert next_hop == gw, 'Datagrama encaminhado para next_hop incorreto'
        assert calc_checksum(payload) == 0, 'Seu checksum está incorreto. Você está calculando sobre todo o payload ICMP?'
        icmp_type, icmp_code = struct.unpack('!BB', payload[:2])
        assert icmp_type == 11, 'O tipo de mensagem ICMP deveria ser 11 - Time Exceeded, mas foi %d' % icmp_type
        assert icmp_code == 0, 'O código de mensagem ICMP deveria ser 0 - Time-to-live exceeded in transit, mas foi %d' % icmp_code
        # Os 4 bytes seguintes a type, code e checksum podem ter qualquer valor - eles são ignorados
        # A partir do oitavo byte, deve vir o início do datagrama que foi descartado
        assert payload[8:] == datagrama[:28], 'A mensagem ICMP deveria conter os primeiros 28 bytes (cabeçalho + 8 bytes de payload) do datagrama IP que foi descartado'
    else:
        assert len(enlace.fila) == 1, 'Só foi recebido um datagrama, mas foi encaminhado mais de um'
        datagrama, next_hop = enlace.fila.pop()
        assert len(datagrama) == 20, 'O tamanho mudou ao ser encaminhado'
        dscp, ecn, identification, flags, frag_offset, ttl_, proto, \
               src_addr, dst_addr, payload = read_ipv4_header(datagrama, verify_checksum=True)
        assert ttl_ == ttl - 1, 'Foi utilizado um TTL de %d, mas deveria ter sido %d' % (ttl_, ttl - 1)
        assert dscp == 0 and ecn == 0 and identification == 0 and flags == 0 and frag_offset == 0 and \
               proto == IPPROTO_TCP and src_addr=='1.2.3.4' and dst_addr==dest and \
               len(payload) == 0, 'Foram alteradas informações do datagrama original'
        assert next_hop == gw, 'Datagrama encaminhado para next_hop incorreto'

# Testa roteador com uma única rota padrão
gw = rand_ip()
myip = rand_ip()
rede.definir_endereco_host(myip)
rede.definir_tabela_encaminhamento([
    ('0.0.0.0/0', gw),
])
for i in range(128):
    enviar_datagrama(rand_ip(), random.randint(1, 255), gw, myip)
    for j in range(random.randint(0, 2)):
        enviar_datagrama(rand_ip(), 1, gw, myip)

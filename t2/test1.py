#!/usr/bin/env python3
import random
from mytcputils import *
from mytcp import Servidor

class CamadaRede:
    def __init__(self):
        self.callback = None
        self.fila = []
    def registrar_recebedor(self, callback):
        self.callback = callback
    def enviar(self, segmento, dest_addr):
        self.fila.append((segmento, dest_addr))

foi_aceita = False
def conexao_aceita(conexao):
    global foi_aceita
    foi_aceita = True

rede = CamadaRede()
dst_port = random.randint(10, 1023)
servidor = Servidor(rede, dst_port)
servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)

src_port = random.randint(1024, 0xffff)
seq_no = random.randint(0, 0xffff)
src_addr, dst_addr = '10.0.0.%d'%random.randint(1, 10), '10.0.0.%d'%random.randint(11, 20)
assert rede.fila == []
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
assert foi_aceita, 'O monitor de conexões aceitas deveria ter sido chamado'
assert len(rede.fila) == 1
segmento, dst_addr2 = rede.fila[0]
assert fix_checksum(segmento, src_addr, dst_addr) == segmento
src_port2, dst_port2, seq_no2, ack_no2, flags2, _, _, _ = read_header(segmento)
assert 4*(flags2>>12) == len(segmento), 'O SYN+ACK não deveria ter payload'
assert dst_addr2 == src_addr
assert src_port2 == dst_port
assert dst_port2 == src_port
assert ack_no2 == seq_no + 1
assert flags2 & (FLAGS_SYN|FLAGS_ACK) == (FLAGS_SYN|FLAGS_ACK)
assert flags2 & (FLAGS_FIN|FLAGS_RST) == 0

rede.fila.clear()
src_port3 = src_port
while src_port3 == src_port:
    src_port3 = random.randint(1024, 0xffff)
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port3, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
assert len(rede.fila) == 1
segmento, dst_addr4 = rede.fila[0]
assert fix_checksum(segmento, src_addr, dst_addr) == segmento
src_port4, dst_port4, seq_no4, ack_no4, flags4, _, _, _ = read_header(segmento)
assert 4*(flags4>>12) == len(segmento), 'O SYN+ACK não deveria ter payload'
assert dst_addr4 == src_addr
assert src_port4 == dst_port
assert dst_port4 == src_port3
assert ack_no4 == seq_no + 1
assert seq_no4 != seq_no2, 'O primeiro número de sequência usado em uma conexão deveria ser aleatório'
assert flags4 & (FLAGS_SYN|FLAGS_ACK) == (FLAGS_SYN|FLAGS_ACK)
assert flags4 & (FLAGS_FIN|FLAGS_RST) == 0

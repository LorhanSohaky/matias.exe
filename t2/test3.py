#!/usr/bin/env python3
import os
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

recebido = b''
def dados_recebidos(c, dados):
    global recebido
    recebido += dados

conexao = None
def conexao_aceita(c):
    global conexao
    conexao = c
    c.registrar_recebedor(dados_recebidos)

rede = CamadaRede()
dst_port = random.randint(10, 1023)
servidor = Servidor(rede, dst_port)
servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)

src_port = random.randint(1024, 0xffff)
seq_no = random.randint(0, 0xffff)
src_addr, dst_addr = '10.%d.1.%d'%(random.randint(1, 10), random.randint(0,255)), '10.%d.1.%d'%(random.randint(11, 20), random.randint(0, 255))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
segmento, _ = rede.fila[0]
_, _, ack_no, ack, flags, _, _, _ = read_header(segmento)
assert 4*(flags>>12) == len(segmento), 'O SYN+ACK não deveria ter payload'
assert (flags & FLAGS_ACK) == FLAGS_ACK
rede.fila.clear()

seq_no += 1
ack_no += 1
assert ack == seq_no

rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))
rede.fila.clear()

payload = os.urandom(MSS)
conexao.enviar(payload)
assert len(rede.fila) == 1
segmento, _ = rede.fila[0]
_, _, seq, ack, flags, _, _, _ = read_header(segmento)
assert seq == ack_no
assert (flags & FLAGS_ACK) == FLAGS_ACK and ack == seq_no
assert segmento[4*(flags>>12):] == payload
ack_no += MSS
rede.fila.clear()

payload = b'hello world'
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
seq_no += len(payload)
assert recebido == payload
recebido = b''
rede.fila.clear()

for i in range(5):
    nseg = random.randint(2,10)
    payload = os.urandom(nseg*MSS)
    conexao.enviar(payload)
    for j in range(nseg):
        segmento, _ = rede.fila.pop(0)
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        assert seq == ack_no
        assert (flags & FLAGS_ACK) == FLAGS_ACK and ack == seq_no
        assert segmento[4*(flags>>12):] == payload[j*MSS:(j+1)*MSS]
        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

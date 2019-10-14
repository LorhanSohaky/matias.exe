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

recebido = None
def dados_recebidos(c, dados):
    global recebido
    recebido = dados

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

rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_FIN|FLAGS_ACK), src_addr, dst_addr))
seq_no += 1
assert recebido == b''

assert len(rede.fila) == 1
segmento, _ = rede.fila[0]
_, _, _, ack, flags, _, _, _ = read_header(segmento)
assert 4*(flags>>12) == len(segmento), 'O servidor não enviou dados, então não deveria haver payload'
assert (flags & FLAGS_ACK) == FLAGS_ACK
assert ack == seq_no
rede.fila.clear()

conexao.fechar()
segmento, _ = rede.fila[0]
_, _, seq, ack, flags, _, _, _ = read_header(segmento)
assert (flags & FLAGS_FIN) == FLAGS_FIN
assert seq == ack_no
if (flags & FLAGS_ACK) == FLAGS_ACK:
    assert ack == seq_no
ack_no += 1

rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

recebido = None
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + os.urandom(MSS), src_addr, dst_addr))
assert recebido is None, 'A conexão não deve receber dados depois de ter sido fechada'

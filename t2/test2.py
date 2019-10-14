#!/usr/bin/env python3
import os
import random
from collections import OrderedDict
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

seq_list = []
ack_list = OrderedDict()
esperado = b''
recebido = b''
def dados_recebidos(conexao, dados):
    global recebido
    recebido += dados

def conexao_aceita(conexao):
    conexao.registrar_recebedor(dados_recebidos)

rede = CamadaRede()
dst_port = random.randint(10, 1023)
servidor = Servidor(rede, dst_port)
servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)

src_port = random.randint(1024, 0xffff)
seq_no = random.randint(0, 0xffff)
src_addr, dst_addr = '172.16.%d.%d'%(random.randint(1, 10), random.randint(0,255)), '172.16.%d.%d'%(random.randint(11, 20), random.randint(0, 255))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
segmento, _ = rede.fila[0]
_, _, ack_no, ack, flags, _, _, _ = read_header(segmento)
assert 4*(flags>>12) == len(segmento), 'O SYN+ACK não deveria ter payload'
assert (flags & FLAGS_ACK) == FLAGS_ACK
ack_list[ack] = None
rede.fila.clear()

seq_no += 1
ack_no += 1

payload = os.urandom(random.randint(16, MSS))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
payload = os.urandom(random.randint(4, MSS))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))

payload = b'ola'
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
seq_list.append(seq_no)
seq_no += len(payload)
esperado += payload

payload = b', '
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no-3, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
seq_list.append(seq_no)
seq_no += len(payload)
esperado += payload

payload = b'mundo'
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no-random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no-2, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+2, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
seq_list.append(seq_no)
seq_no += len(payload)
esperado += payload

print('esperado: %r' % esperado)
print('recebido: %r' % recebido)
assert esperado == recebido

payload = os.urandom(random.randint(16, MSS))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
payload = os.urandom(MSS)
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))

payload = os.urandom(random.randint(16, MSS))
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
seq_list.append(seq_no)
seq_no += len(payload)
esperado += payload

payload = os.urandom(MSS)
rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
seq_list.append(seq_no)
seq_no += len(payload)
seq_list.append(seq_no)
esperado += payload

assert esperado == recebido

for segmento, _ in rede.fila:
    _, _, _, ack, flags, _, _, _ = read_header(segmento)
    assert 4*(flags>>12) == len(segmento), 'Este teste não gera envios: não deveria haver payloads'
    if (flags & FLAGS_ACK) == FLAGS_ACK:
        ack_list[ack] = None

ack_list = list(ack_list.keys())
print('ACKs esperados: %r' % seq_list)
print('ACKs recebidos: %r' % ack_list)
assert seq_list == ack_list

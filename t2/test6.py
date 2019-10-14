#!/usr/bin/env python3
import os
import random
import asyncio
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

@asyncio.coroutine
def main():
    global recebido, conexao

    rede = CamadaRede()
    dst_port = random.randint(10, 1023)
    servidor = Servidor(rede, dst_port)
    servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)

    src_port = random.randint(1024, 0xffff)
    seq_no = random.randint(0, 0xffff)
    src_addr, dst_addr = '10.%d.%d.%d'%(random.randint(1, 10), random.randint(0,255), random.randint(0,255)), '10.%d.%d.%d'%(random.randint(11,20), random.randint(0,255), random.randint(0,255))
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

    yield from asyncio.sleep(0.1)

    while len(rede.fila) > 0:
        segmento, _ = rede.fila.pop(0)
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        assert seq == ack_no
        assert (flags & FLAGS_ACK) == FLAGS_ACK and ack == seq_no
        assert segmento[4*(flags>>12):] == payload

    ack_no += MSS
    rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

    payload = os.urandom(MSS)
    conexao.enviar(payload)
    assert len(rede.fila) == 1
    rede.fila.clear()  # descarta

    # sample_rtt = 0.1
    # estimated_rtt = sample_rtt = 0.1
    # dev_rtt = sample_rtt/2 = 0.05
    # timeout_interval = estimated_rtt + 4*dev_rtt  = 0.3
    # 0.29 < timeout_interval < 0.31
    yield from asyncio.sleep(0.29)
    assert len(rede.fila) == 0, 'Não deveria ter retransmitido ainda'
    yield from asyncio.sleep(0.02)
    assert len(rede.fila) == 1, 'Já deveria ter retransmitido'

    segmento, _ = rede.fila.pop(0)
    _, _, seq, ack, flags, _, _, _ = read_header(segmento)
    assert seq == ack_no
    assert (flags & FLAGS_ACK) == FLAGS_ACK and ack == seq_no
    assert segmento[4*(flags>>12):] == payload

    # Verifica se o tempo de segmentos retransmitidos está sendo ignorado
    yield from asyncio.sleep(2)
    rede.fila.clear()
    ack_no += MSS
    rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))
    payload = os.urandom(MSS)
    conexao.enviar(payload)
    assert len(rede.fila) == 1
    rede.fila.clear()  # descarta
    yield from asyncio.sleep(0.25)
    assert len(rede.fila) == 0, 'Não deveria ter retransmitido ainda'
    yield from asyncio.sleep(0.06)
    assert len(rede.fila) == 1, 'Já deveria ter retransmitido'
    segmento, _ = rede.fila.pop(0)
    _, _, seq, ack, flags, _, _, _ = read_header(segmento)
    assert seq == ack_no
    assert (flags & FLAGS_ACK) == FLAGS_ACK and ack == seq_no
    assert segmento[4*(flags>>12):] == payload
    ack_no += MSS
    rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

    payload = os.urandom(MSS)
    conexao.enviar(payload)
    yield from asyncio.sleep(0.001)
    assert len(rede.fila) == 1
    segmento, _ = rede.fila.pop(0)
    _, _, seq, ack, flags, _, _, _ = read_header(segmento)
    assert seq == ack_no
    assert (flags & FLAGS_ACK) == FLAGS_ACK and ack == seq_no
    assert segmento[4*(flags>>12):] == payload
    ack_no += MSS
    rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

    payload = os.urandom(MSS)
    conexao.enviar(payload)
    assert len(rede.fila) == 1
    rede.fila.clear()  # descarta

    # sample_rtt = 0.001
    # estimated_rtt = (1-0.125)*0.1 + 0.125*0.001 = 0.087625
    # dev_rtt = (1-0.25)*0.05 + 0.25*abs(0.001-0.1) = 0.06225
    # timeout_interval = estimated_rtt + 4*dev_rtt = 0.336625
    # 0.32 < timeout_interval < 0.34
    yield from asyncio.sleep(0.32)
    assert len(rede.fila) == 0, 'Não deveria ter retransmitido ainda'
    yield from asyncio.sleep(0.02)
    assert len(rede.fila) == 1, 'Já deveria ter retransmitido'

    segmento, _ = rede.fila.pop(0)
    _, _, seq, ack, flags, _, _, _ = read_header(segmento)
    assert seq == ack_no
    assert (flags & FLAGS_ACK) == FLAGS_ACK and ack == seq_no
    assert segmento[4*(flags>>12):] == payload
    ack_no += MSS
    rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

asyncio.get_event_loop().run_until_complete(main())

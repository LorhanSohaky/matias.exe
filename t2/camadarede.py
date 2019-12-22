# Antes de usar, execute o seguinte comando para evitar que o Linux feche
# as conexões TCP que o seu programa estiver tratando:
#
# sudo iptables -I OUTPUT -p tcp --tcp-flags RST RST -j DROP

import socket
import asyncio
from mytcputils import *


class CamadaRedeLinux:
    def __init__(self):
        self.fd = socket.socket(
            socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.meu_endereco = self.fd.getsockname()[0]
        self.minha_porta = self.fd.getsockname()[1]
        asyncio.get_event_loop().add_reader(self.fd, self.__raw_recv)
        self.callback = None

    def __handle_ipv4_header(packet):
        version = packet[0] >> 4
        ihl = packet[0] & 0xf
        assert version == 4
        src_addr = addr2str(packet[12:16])
        dst_addr = addr2str(packet[16:20])
        segment = packet[4*ihl:]
        return src_addr, dst_addr, segment

    def __raw_recv(self):
        # número suficientemente grande para a maioria das camadas de enlace
        packet = self.fd.recv(12000)
        src_addr, dst_addr, segment = CamadaRedeLinux.__handle_ipv4_header(
            packet)

        if self.callback:
            self.callback(src_addr, dst_addr, segment)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de rede
        """
        self.callback = callback

    def enviar(self, segmento, dest_addr):
        """
        Envia segmento para dest_addr, onde dest_addr é um endereço IPv4
        fornecido como string (no formato x.y.z.w).
        """
        self.fd.sendto(segmento, (dest_addr, 0))

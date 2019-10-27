import socket
import asyncio


class CamadaEnlaceLinux:
    def __init__(self):
        self.fd = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.fd.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        asyncio.get_event_loop().add_reader(self.fd, self.__raw_recv)
        self.callback = None

    def __raw_recv(self):
        datagrama = self.fd.recv(12000)  # número suficientemente grande para a maioria das camadas de enlace
        if self.callback:
            self.callback(datagrama)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar qual enlace está na mesma subrede
        que o next_hop e descobrir o endereço MAC correspondente (via ARP).
        """
        self.fd.sendto(datagrama, (next_hop, 0))

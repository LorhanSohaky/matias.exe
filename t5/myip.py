from myiputils import *
from mytcputils import *
from ipaddress import ip_network, ip_address
from random import randint

def make_icmp(datagrama):
    unused = 0
    checksum = 0
    tipo = 11
    codigo = 0
    payload = datagrama[:28]
    comprimento = 8 + len(payload)
    
    icmp = struct.pack('!bbhi', tipo, codigo, checksum, comprimento) + payload

    checksum = twos_comp(calc_checksum(icmp), 16)
    icmp = struct.pack('!bbhi', tipo, codigo, checksum, comprimento) + payload

    return icmp


class CamadaRede:
    def __init__(self, enlace):
        """
        Inicia a camada de rede. Recebe como argumento uma implementação
        de camada de enlace capaz de localizar os next_hop (por exemplo,
        Ethernet com ARP).
        """
        self.callback = None
        self.enlace = enlace
        self.enlace.registrar_recebedor(self.__raw_recv)
        self.meu_endereco = None
        self.tabela = None

    def __raw_recv(self, datagrama):
        dscp, ecn, identification, flags, frag_offset, ttl, proto, \
            src_addr, dst_addr, payload = read_ipv4_header(datagrama)
        if dst_addr == self.meu_endereco:
            # atua como host
            if proto == IPPROTO_TCP and self.callback:
                self.callback(src_addr, dst_addr, payload)
        else:
            # atua como roteador
            ttl = ttl - 1
            next_hop = self._next_hop(dst_addr)

            if ttl > 0:
                header = make_ipv4_header(len(payload), src_addr, dst_addr, dscp, ecn,
                                          identification, flags, frag_offset, ttl, proto, verify_checksum=True)
                datagrama = header + payload
                self.enlace.enviar(datagrama, next_hop)
            else:
                next_hop = self._next_hop(src_addr)
                icmp = make_icmp(datagrama)
                new_header = make_ipv4_header(len(icmp), self.meu_endereco, src_addr, dscp, ecn,
                                          identification, flags, frag_offset, randint(100,255), IPPROTO_ICMP, verify_checksum=True)
                self.enlace.enviar(new_header+icmp, next_hop)

    def _next_hop(self, dest_addr):
        # TODO: Use a tabela de encaminhamento para determinar o próximo salto
        # (next_hop) a partir do endereço de destino do datagrama (dest_addr).
        # Retorne o next_hop para o dest_addr fornecido.
        dest_addr = ip_address(dest_addr)

        for item in self.tabela:
            network = item[0]
            if dest_addr in network:
                return str(item[1])

        return None

    def definir_endereco_host(self, meu_endereco):
        """
        Define qual o endereço IPv4 (string no formato x.y.z.w) deste host.
        Se recebermos datagramas destinados a outros endereços em vez desse,
        atuaremos como roteador em vez de atuar como host.
        """
        self.meu_endereco = meu_endereco

    def definir_tabela_encaminhamento(self, tabela):
        """
        Define a tabela de encaminhamento no formato
        [(cidr0, next_hop0), (cidr1, next_hop1), ...]

        Onde os CIDR são fornecidos no formato 'x.y.z.w/n', e os
        next_hop são fornecidos no formato 'x.y.z.w'.
        """
        # AQUI A MÁGICA!!!
        self.tabela = [(ip_network(item[0]), ip_address(item[1]))
                       for item in tabela]
        self.tabela.sort(key=lambda tup: tup[0].prefixlen)
        self.tabela.reverse()

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de rede
        """
        self.callback = callback

    def enviar(self, segmento, dest_addr):
        """
        Envia segmento para dest_addr, onde dest_addr é um endereço IPv4
        (string no formato x.y.z.w).
        """
        next_hop = self._next_hop(dest_addr)
        header = make_ipv4_header(
            len(segmento), self.meu_endereco, dest_addr, verify_checksum=True)
        self.enlace.enviar(header+segmento, next_hop)

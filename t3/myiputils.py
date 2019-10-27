import struct
# Funções que foram usadas no TCP e também são úteis
# para a implementação do protocolo IP
from mytcputils import str2addr, addr2str, calc_checksum


IPPROTO_ICMP = 1
IPPROTO_TCP = 6


def read_ipv4_header(datagram, verify_checksum=False):
    # https://en.wikipedia.org/wiki/IPv4#Header
    vihl, dscpecn, total_len, identification, flagsfrag, ttl, proto, \
        checksum, src_addr, dest_addr = \
        struct.unpack('!BBHHHBBHII', datagram[:20])
    version = vihl >> 4
    ihl = vihl & 0xf
    assert version == 4
    dscp = dscpecn >> 2
    ecn = dscpecn & 0b11
    flags = flagsfrag >> 13
    frag_offset = flagsfrag & 0x1fff
    src_addr = addr2str(datagram[12:16])
    dst_addr = addr2str(datagram[16:20])
    if verify_checksum:
        assert calc_checksum(datagram[:4*ihl]) == 0
    payload = datagram[4*ihl:total_len]

    return dscp, ecn, identification, flags, frag_offset, ttl, proto, \
           src_addr, dst_addr, payload

import struct
# Funções que foram usadas no TCP e também são úteis
# para a implementação do protocolo IP
from mytcputils import str2addr, addr2str, calc_checksum

from random import randint


IPPROTO_ICMP = 1
IPPROTO_TCP = 6

IHL = 5
TTL = 255


def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val


def make_ipv4_header(size, src_addr, dest_addr, dscp=None, ecn=None, identification=None, flags=None, frag_offset=None, ttl=255, proto=None, verify_checksum=False):
    version = 4 << 4
    ihl = IHL
    vihl = version + ihl

    if dscp is None:
        dscp = 0 << 6
    if ecn is None:
        ecn = 0

    dscpecn = dscp + ecn

    total_length = twos_comp(size + 20, 16)

    if identification is None:
        identification = twos_comp(randint(0, 2**16), 16)

    if flags is None:
        flag_rsv = 0
        flag_dtf = 0
        flag_mrf = 0
        flags = (flag_rsv << 15) | (flag_dtf << 14) | (flag_mrf << 13)

    if frag_offset is None:
        frag_offset = 0

    flags |= frag_offset

    ttl = twos_comp(ttl, 8)

    if proto is None:
        proto = IPPROTO_TCP

    checksum = 0
    src_addr = str2addr(src_addr)
    dest_addr = str2addr(dest_addr)
    header = struct.pack('!bbhhhbbh', vihl, dscpecn, total_length,
                         identification, flags, ttl, proto, checksum) + src_addr + dest_addr

    if verify_checksum:
        checksum = twos_comp(calc_checksum(header[:4*ihl]), 16)
        header = struct.pack('!bbhhhbbh', vihl, dscpecn, total_length,
                             identification, flags, ttl, proto, checksum) + src_addr + dest_addr

    return header


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

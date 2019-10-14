import struct

# Valores das flags que serão usadas na nossa implementação simplificada
FLAGS_FIN = 1<<0
FLAGS_SYN = 1<<1
FLAGS_RST = 1<<2
FLAGS_ACK = 1<<4

MSS = 1460   # Tamanho do payload de um segmento TCP (em bytes)


def make_header(src_port, dst_port, seq_no, ack_no, flags):
    """
    Constrói um cabeçalho TCP simplificado.

    Consulte o formato completo em https://en.wikipedia.org/wiki/Transmission_Control_Protocol#TCP_segment_structure
    """
    return struct.pack('!HHIIHHHH',
                       src_port, dst_port, seq_no, ack_no, (5<<12)|flags,
                       8*MSS, 0, 0)


def read_header(segment):
    """
    Lê um cabeçalho
    """
    src_port, dst_port, seq_no, ack_no, \
        flags, window_size, checksum, urg_ptr = \
        struct.unpack('!HHIIHHHH', segment[:20])
    return src_port, dst_port, seq_no, ack_no, \
        flags, window_size, checksum, urg_ptr


def calc_checksum(data):
    """
    Calcula o checksum complemento-de-um (formato do TCP e do UDP) para os
    dados fornecidos.
    """
    if len(data) % 2 == 1:
        # se for ímpar, faz padding à direita
        data += b'\x00'
    checksum = 0
    for i in range(0, len(data), 2):
        x, = struct.unpack('!H', data[i:i+2])
        checksum += x
        while checksum > 0xffff:
            checksum = (checksum & 0xffff) + 1
    checksum = ~checksum
    return checksum & 0xffff


def addr2str(addr):
    """
    Converte um endereço IPv4 binário para uma string (no formato x.y.z.w)
    """
    return '%d.%d.%d.%d' % tuple(int(x) for x in addr)


def str2addr(addr):
    """
    Converte uma string (no formato x.y.z.w) para um endereço IPv4 binário
    """
    return bytes(int(x) for x in addr.split('.'))


def fix_checksum(segment, src_addr, dst_addr):
    """
    Corrige o checksum de um segmento TCP. É necessário passar os endereços
    IPv4 de origem e de destino, já que apesar de não fazerem parte da camada
    de transporte, eles são incluídos no pseudocabeçalho, que faz parte do
    cálculo do checksum.

    Os endereços IPv4 devem ser passados como string (no formato x.y.z.w)
    """
    pseudohdr = str2addr(src_addr) + str2addr(dst_addr) + \
        struct.pack('!HH', 0x0006, len(segment))
    seg = bytearray(segment)
    seg[16:18] = b'\x00\x00'
    seg[16:18] = struct.pack('!H', calc_checksum(pseudohdr + seg))
    return bytes(seg)

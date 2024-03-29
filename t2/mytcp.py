import asyncio
from mytcputils import FLAGS_FIN, FLAGS_SYN, FLAGS_ACK, MSS, make_header, read_header, fix_checksum
import random
import math
import time

DEBUG = True


class Servidor:
    def __init__(self, rede, porta):
        self.rede = rede
        self.porta = porta
        self.conexoes = {}
        self.callback = None
        self.rede.registrar_recebedor(self._rdt_rcv)

    def registrar_monitor_de_conexoes_aceitas(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que uma nova conexão for aceita
        """
        self.callback = callback

    def _start_connection(self, id_conexao, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, _, _, _ = read_header(segment)
        src_addr, src_port, dst_addr, dst_port = id_conexao

        ack_no = seq_no + 1
        seq_no = random.randint(40, 0xfff)
        cabecalho = make_header(
            dst_port, src_port, seq_no, ack_no, FLAGS_SYN | FLAGS_ACK)
        cabecalho = fix_checksum(cabecalho, src_addr, dst_addr)
        self.rede.enviar(cabecalho, src_addr)
        print(f'{src_addr}:{src_port}',
              'connected with', f'{dst_addr}:{dst_port}')
        print('handshaking: seq->', seq_no, 'ack->', ack_no)
        return Conexao(self, id_conexao, seq_no + 1, ack_no)

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, _, _, _ = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return

        payload = segment[4*(flags>>12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN:
            conexao = self.conexoes[id_conexao] = self._start_connection(
                id_conexao, segment)

            if self.callback:
                self.callback(conexao)
        elif id_conexao in self.conexoes:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexoes[id_conexao]._rdt_rcv(seq_no, ack_no, flags, payload)
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Cliente:
    def __init__(self, rede, porta):
        self.rede = rede
        self.porta = porta
        self.conexao = None
        self.callback = None
        self.rede.registrar_recebedor(self._rdt_rcv)
        self.id_conexao = None
        self.status_conexao = None
        # 0 = Não conectado
        # 1 = Conectando
        # 2 = Conectado
    
    def enviar(self, dados):
        self.conexao.enviar(dados)

    def registrar_monitor_de_conexoes_aceitas(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que uma nova conexão for aceita
        """
        self.callback = callback

    def start_connection(self, dst_addr, dst_port):
        src_addr = self.rede.meu_endereco
        src_port = self.porta

        ack_no = 0
        seq_no = 0
        
        cabecalho = make_header(
            src_port, dst_port, seq_no, ack_no, FLAGS_SYN)
        cabecalho = fix_checksum(cabecalho, src_addr, dst_addr)
        self.rede.enviar(cabecalho, dst_addr)
        print(f'{src_addr}:{src_port}',
              'connecting with', f'{dst_addr}:{dst_port}')
        print('handshaking: seq->', seq_no, 'ack->', ack_no)
        self.status_conexao = 1

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, _, _, _ = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return

        payload = segment[4*(flags >> 12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN and self.status_conexao == 1:
            tmp = ack_no
            ack_no = seq_no + 1
            seq_no = tmp

            self.id_conexao = id_conexao

            cabecalho = make_header(
                dst_port, src_port, seq_no, ack_no, FLAGS_ACK)
            cabecalho = fix_checksum(cabecalho, src_addr, dst_addr)
            self.rede.enviar(cabecalho, src_addr)

            self.conexao = Conexao(
                self, id_conexao, seq_no, ack_no)

            self.status_conexao = 2

            if self.callback:
                self.callback(self.conexao)
        elif id_conexao == self.id_conexao and self.status_conexao == 2:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexao._rdt_rcv(seq_no, ack_no, flags, payload)
        elif self.status_conexao != 2:
            print('%s:%d -> %s:%d (conexão não estabelecida)' %
                  (src_addr, src_port, dst_addr, dst_port))
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Conexao:
    def __init__(self, servidor, id_conexao, seq_no, ack_no):
        self.servidor = servidor
        self.id_conexao = id_conexao
        self.callback = None
        self.timer = None
        self.nao_confirmados = b''
        self.seq_no = seq_no
        self.ack_no = ack_no
        self.send_base = seq_no

        self.first = True
        self.initial_moment = None
        self.final_moment = None
        self.timeout_interval = 2
        self.sample_rtt = None
        self.estimated_rtt = None
        self.dev_rtt = None
        self.retransmitindo = False

        self.nao_enviados = b''
        self.janela = 1
        self.last_seq = None
        self.closing = False

    def _start_timer(self):
        self._stop_timer()
        self.timer = asyncio.get_event_loop().call_later(self.timeout_interval, self._timeout)

    def _stop_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _timeout(self):
        if DEBUG:
            print('---Timeout---')
        self.timer = None
        self._retransmit()
        self._start_timer()

    def _retransmit(self):
        self.retransmitindo = True
        self.janela = self.janela // 2
        comprimento = min(MSS, len(self.nao_confirmados))
        msg = self.nao_confirmados[:comprimento]
        if DEBUG:
            _, _, dst_addr, _ = self.id_conexao
            print(dst_addr, 'retransmiting: seq->', self.send_base, 'ack->', self.ack_no,
                      'bytes->', len(msg), ('timer-> %.3f' % self.timeout_interval) if self.timer is None else ('timer -> anterior'))
        self._send_ack_segment(msg)


    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        src_addr, src_port, dst_addr, dst_port = self.id_conexao

        if self.ack_no == seq_no:

            if DEBUG:
                print(f'{src_addr}:{src_port}', 'receiving: seq->', seq_no, 'ack->', ack_no, 'bytes->', len(payload))

            if (flags & FLAGS_FIN) == FLAGS_FIN and not self.closing:
                self.closing = True
                self.callback(self, b'')
                self.ack_no += 1
                src_addr, src_port, dst_addr, dst_port = self.id_conexao
                cabecalho = make_header(
                    dst_port, src_port, self.seq_no, self.ack_no, FLAGS_FIN | FLAGS_ACK)
                cabecalho = fix_checksum(cabecalho, dst_addr, src_addr)
                self.servidor.rede.enviar(cabecalho, src_addr)
                return
            elif (flags & FLAGS_ACK) == FLAGS_ACK and self.closing:
                print(f'Fechada a conexão com {src_addr}:{src_port}')
                self.servidor.conexoes.pop(self.id_conexao)
                return

            if ack_no > self.send_base and (flags & FLAGS_ACK) == FLAGS_ACK:
                self.nao_confirmados = self.nao_confirmados[ack_no-self.send_base:]
                self.send_base = ack_no

                if self.nao_confirmados:
                    if DEBUG:
                        print('++Timer restarted++')
                    self._start_timer()
                else:
                    if DEBUG:
                        print('++Timer stopped++')
                    self._stop_timer()
                    if not self.retransmitindo:
                        self.final_moment = time.time()
                        self.calc_rtt()

            if self.last_seq == ack_no:
                self.janela += 1
                if DEBUG:
                    print('Updated window', self.janela, 'MSS')
                self._send_pending()

            self.retransmitindo = False
            self.ack_no += len(payload)

            if len(payload) > 0:  # Só Deus sabe, mas funciona
                dados = make_header(src_port, dst_port, self.seq_no, self.ack_no, flags)
                dados = fix_checksum(dados, src_addr,dst_addr)
                self.servidor.rede.enviar(dados,src_addr)

                self.callback(self, payload)

    def registrar_recebedor(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que dados forem corretamente recebidos
        """
        self.callback = callback

    def enviar(self, dados):
        """
        Usado pela camada de aplicação para enviar dados
        """

        self.nao_enviados += dados
        prontos_para_envio = self.nao_enviados[:(self.janela * MSS)]
        self.nao_enviados = self.nao_enviados[(self.janela * MSS):]

        self.last_seq = self.seq_no + len(prontos_para_envio)
        if DEBUG:
            print( 'Last seq', self.last_seq)

        numero_de_segmentos = math.ceil(len(prontos_para_envio) / MSS)
        if numero_de_segmentos == 0: # Caso seja uma mensagem em que o tamanho dos dados seja < MSS
            numero_de_segmentos = 1
        for i in range(numero_de_segmentos):
            msg = prontos_para_envio[i*MSS:(i+1)*MSS]
            if self.timer is None:
                if DEBUG:
                    print('++Timer started++')
                    _, _, dst_addr, _ = self.id_conexao
                    print(dst_addr, 'sending: seq->', self.seq_no, 'ack->', self.ack_no,
                        'bytes->', len(msg), ('timer-> %.3f' % self.timeout_interval) if self.timer is None else ('timer -> anterior'))
            self._send_ack_segment(msg)

    def _send_pending(self):
        if DEBUG:
            print('Enviando pendentes')
        tamanho_pendentes = (self.janela * MSS ) - len(self.nao_confirmados)

        if tamanho_pendentes > 0:
            prontos_para_envio = self.nao_enviados[:tamanho_pendentes]
            if len(prontos_para_envio) == 0:
                return
            self.nao_enviados = self.nao_enviados[tamanho_pendentes:]
            self.last_seq = self.seq_no + len(prontos_para_envio)
            if DEBUG:
                print('Last seq', self.last_seq)

            numero_de_segmentos = math.ceil(len(prontos_para_envio) / MSS)
            if numero_de_segmentos == 0:  # Caso seja uma mensagem em que o tamanho dos dados seja < MSS
                numero_de_segmentos = 1
            for i in range(numero_de_segmentos):
                msg = prontos_para_envio[i*MSS:(i+1)*MSS]
                if self.timer is None:
                    if DEBUG:
                        print('++Timer started++')
                        _, _, dst_addr, _ = self.id_conexao
                        print(dst_addr, 'sending: seq->', self.seq_no, 'ack->', self.ack_no,
                            'bytes->', len(msg), ('timer-> %.3f' % self.timeout_interval) if self.timer is None else ('timer -> anterior'))
                self._send_ack_segment(msg)


    def _send_ack_segment(self, payload):
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        seq_no = None
        if self.retransmitindo:
            seq_no = self.send_base
        else:
            seq_no = self.seq_no
            self.seq_no += len(payload)
            self.nao_confirmados = self.nao_confirmados + payload
        cabecalho = make_header(dst_port, src_port, seq_no, self.ack_no, FLAGS_ACK)
        segmento = fix_checksum(cabecalho + payload, dst_addr, src_addr)
        self.servidor.rede.enviar(segmento, src_addr)


        if self.timer is None:
            self.initial_moment = time.time()
            self._start_timer()


    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        cabecalho = make_header(dst_port, src_port, self.seq_no, self.ack_no, FLAGS_FIN)
        cabecalho = fix_checksum(cabecalho, dst_addr, src_addr)
        self.servidor.rede.enviar(cabecalho, src_addr)

    def calc_rtt(self):
        alfa = 0.125
        beta = 0.25

        self.sample_rtt = self.final_moment - self.initial_moment

        if self.first:
            self.first = not self.first
            
            self.estimated_rtt = self.sample_rtt
            self.dev_rtt = self.sample_rtt / 2
        else:
            self.estimated_rtt = (1 - alfa) * self.estimated_rtt + alfa * self.sample_rtt
            self.dev_rtt = (1 - beta) * self.dev_rtt + beta * abs(self.sample_rtt - self.estimated_rtt)

        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt
        if DEBUG:
            print('New timeout %.3f' % self.timeout_interval)

    def __str__(self):
        src_addr, src_port, _, _ = self.id_conexao
        return f'{src_addr}:{src_port}'

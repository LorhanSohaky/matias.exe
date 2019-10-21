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

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, _, _, _ = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return

        payload = segment[4*(flags>>12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN:
            conexao = self.conexoes[id_conexao] = Conexao(self, id_conexao, seq_no)

            if self.callback:
                self.callback(conexao)
        elif id_conexao in self.conexoes:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexoes[id_conexao]._rdt_rcv(seq_no, ack_no, flags, payload)
            if (flags & FLAGS_FIN) == FLAGS_FIN:
                self.conexoes.pop(id_conexao)
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Conexao:
    def __init__(self, servidor, id_conexao, seq_no):
        self.servidor = servidor
        self.id_conexao = id_conexao
        self.callback = None
        self.timer = None
        self.nao_confirmados = b''
        self.seq_no = random.randint(1,0xfff)
        self.ack_no = seq_no + 1
        self.send_base = seq_no

        self.first = True
        self.initial_moment = None
        self.final_moment = None
        self.timeout_interval = 2
        self.sample_rtt = None
        self.estimated_rtt = None
        self.dev_rtt = None
        self.retransmitindo = False

        self._start_connection()

    def _start_connection(self):
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        cabecalho = make_header(dst_port, src_port,self.seq_no,self.ack_no,FLAGS_SYN | FLAGS_ACK)
        cabecalho = fix_checksum(cabecalho, src_addr, dst_addr)
        self.servidor.rede.enviar(cabecalho,src_addr)
        self.seq_no += 1
        self.send_base = self.seq_no
        if DEBUG:
            print(src_addr, 'connected with', dst_addr)
            print('handshaking: seq->',self.seq_no,'ack->',self.ack_no)

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
        self._retransmit()
        self._start_timer()

    def _retransmit(self):
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        comprimento = min(MSS, len(self.nao_confirmados))
        msg = self.nao_confirmados[:comprimento]
        if DEBUG:
            print(dst_addr,'retransmiting:', 'seq->', self.send_base, 'ack->', self.ack_no, 'timer-> %.3f' % self.timeout_interval)
        cabecalho = make_header(dst_port, src_port, self.send_base, self.ack_no, FLAGS_ACK)
        segmento = fix_checksum(cabecalho + msg, dst_addr, src_addr)
        self.servidor.rede.enviar(segmento, src_addr)
        self._start_timer()
        self.retransmitindo = True



    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        
        if self.ack_no == seq_no:
            if DEBUG:
                print(src_addr, 'receiving: seq->', seq_no, 'ack->', ack_no, 'bytes->', len(payload))

            if not self.initial_moment is None:
                self._stop_timer()
                print('Timer stopped')
                if not self.retransmitindo:
                    self.final_moment = time.time()
                    self.calc_rtt()
                    
                

            self.retransmitindo = False

            if self.nao_confirmados:
                self.nao_confirmados = self.nao_confirmados[ack_no-self.send_base:]
                self.send_base = ack_no
            if ack_no > self.send_base and (flags & FLAGS_ACK) == FLAGS_ACK:
                print('aqui')
                self.send_base = ack_no -1
                if self.nao_confirmados:
                    self._start_timer()
                else:
                    self._stop_timer()

            self.ack_no += len(payload)

            if (flags & FLAGS_FIN) == FLAGS_FIN:
                self.ack_no += 1 # É preciso somar, pois quando é enviada a flag FIN não há payload
                flags = FLAGS_FIN | FLAGS_ACK

            if ((flags & FLAGS_FIN) == FLAGS_FIN) or len(payload) > 0: # Só Deus sabe, mas funciona
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
        src_addr, src_port, dst_addr, dst_port = self.id_conexao

        numero_de_segmentos = math.ceil(len(dados) / MSS)
        if numero_de_segmentos == 0: # Caso seja uma mensagem em que o tamanho dos dados seja < MSS
            numero_de_segmentos = 1
        for i in range(numero_de_segmentos):
            msg = dados[i*MSS:(i+1)*MSS]
            cabecalho = make_header(dst_port, src_port, self.seq_no, self.ack_no, FLAGS_ACK)
            segmento = fix_checksum(cabecalho + msg, dst_addr, src_addr)
            self.servidor.rede.enviar(segmento, src_addr)
            self.nao_confirmados = self.nao_confirmados + msg
            self.seq_no += len(msg)
            if DEBUG:
                print(dst_addr, 'sending: seq->', self.seq_no, 'ack->', self.ack_no,
                      'bytes->', len(msg), 'timer-> %.3f' % self.timeout_interval)

            if self.timer is None:
                print('Timer started')
                self.initial_moment = time.time()
                self._start_timer()


    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        cabecalho = make_header(dst_port, src_port, self.seq_no, self.seq_no, FLAGS_FIN)
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
        print('New timeout %.3f' % self.timeout_interval)

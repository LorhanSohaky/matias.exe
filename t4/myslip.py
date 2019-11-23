import re


class CamadaEnlace:
    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self.callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.dados = b''

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        datagrama = datagrama.replace(b'\xdb', b'\xdb\xdd')
        datagrama = datagrama.replace(b'\xc0', b'\xdb\xdc')

        delimiter = b'\xc0'
        data = delimiter + datagrama + delimiter
        self.linha_serial.enviar(data)

    def __raw_recv(self, dados):
        dados_tmp = self.dados + dados

        regex = b"(\\xc0)?([^\\xc0]+)(\\xc0)"

        matches = re.match(regex, dados_tmp, re.MULTILINE)
        if matches is None:
            self.dados += dados
            return

        matches = re.finditer(regex, dados_tmp, re.MULTILINE)

        position = 0
        for _, match in enumerate(matches, start=1):
            position += len(match.group(0))
            datagrama = match.group(2)
            datagrama = datagrama.replace(b'\xdb\xdc', b'\xc0')
            datagrama = datagrama.replace(b'\xdb\xdd', b'\xdb')
            if match.group(1) and match.group(3):
                self.callback(datagrama)
            elif match.group(3):
                self.callback(datagrama)
        self.dados = dados_tmp[position:]

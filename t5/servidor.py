#!/usr/bin/env python3
# Este é um exemplo de um programa que faz eco, ou seja, envia de volta para
# o cliente tudo que for recebido em uma conexão.

import asyncio
import re
from camadafisica import ZyboSerialDriver
from mytcp import Servidor as Tcp # copie o arquivo da Etapa 2
from myip import CamadaRede       # copie o arquivo da Etapa 3
from myslip import CamadaEnlace   # copie o arquivo da Etapa 4

DEBUG = True

regex_nick = r'^/nick\s([^: ]+)$'
regex_simple = r'^/nick\s(.+)$'

class Server:
    def __init__(self):
        self.clientes = {}

        if DEBUG:
            print('Iniciando servidor!')

    def dados_recebidos(self,conexao, dados):
        if DEBUG:
            print(conexao, 'recebido',dados)
        if dados == b'':
            if DEBUG:
                src_addr, src_port, _, _ = conexao.id_conexao
                print('Fechando conexão com', f'{src_addr}:{src_port}')

            username = self.clientes[conexao].get('username')

            del self.clientes[conexao]
            conexao.fechar()

            if username:
                msg = f'/quit {username}'
                self.broadcast(msg)

        else:
            dados_decodificados = dados.decode()
            self.clientes[conexao]['entrada'] += dados_decodificados

            self.parser(conexao)
            saida_codificada = self.clientes[conexao]['saida'].encode()

    def conexao_aceita(self, conexao):
        self.clientes[conexao] = {'entrada': '', 'saida': '', 'username': None}
        conexao.registrar_recebedor(self.dados_recebidos)   # usa esse mesmo recebedor para toda conexão aceita

    def broadcast(self, msg):
        msg_encoded = msg.encode()
        
        for conexao in self.clientes:
            conexao.enviar(msg_encoded)

    def parser(self, conexao):
        entrada = self.clientes[conexao]['entrada']

        linhas = entrada.splitlines(True)

        pendentes = ''

        username_atual = self.clientes[conexao]['username']

        usernames = []

        for cliente in self.clientes:
            usernames.append(self.clientes[cliente]['username'])

        for index, linha in enumerate(linhas):
            print(f'Line {index}: {linha.encode()}')
            if '\n' in linha:
                linha = linha.rstrip()
                matches_simple = re.search(regex_simple,linha)
                if matches_simple:
                    matches_nick = re.search(regex_nick, linha, re.MULTILINE)
                    if matches_nick:
                        username_novo = matches_nick.group(1)
                        
                        if username_novo in usernames:
                            conexao.enviar('/error\n'.encode())
                        elif username_atual:
                            self.broadcast(f'/renamed {username_atual} {username_novo}\n')
                        else:
                            self.broadcast(f'/joined {username_novo}\n')

                        self.clientes[conexao]['username'] = username_novo
                    else:
                        conexao.enviar('/error\n'.encode())
                else:
                    if username_atual:
                        self.broadcast(f'{username_atual}: {linha}\n')
                    else:
                        conexao.enviar('/error\n'.encode())

            else:
                pendentes += linha

        self.clientes[conexao]['entrada'] = pendentes


server = Server()

# Integração com as demais camadas

driver = ZyboSerialDriver()
linha_serial = driver.obter_porta(4)
pty = driver.expor_porta_ao_linux(5)
outra_ponta = '192.168.123.1'
nossa_ponta = '192.168.123.2'
porta_tcp = 7000

print('Conecte o RX da porta 4 com o TX da porta 5 e vice-versa.')
print('Para conectar a outra ponta da camada física, execute:')
print()
print('sudo slattach -vLp slip {}'.format(pty.pty_name))
print('sudo ifconfig sl0 {} pointopoint {} mtu 1500'.format(outra_ponta, nossa_ponta))
print()
print('Acesse o serviço com o comando: nc {} {}'.format(nossa_ponta, porta_tcp))
print()

enlace = CamadaEnlace({outra_ponta: linha_serial})
rede = CamadaRede(enlace)
rede.definir_endereco_host(nossa_ponta)
rede.definir_tabela_encaminhamento([
    ('0.0.0.0/0', outra_ponta)
])
tcp = Tcp(rede, porta_tcp)
tcp.registrar_monitor_de_conexoes_aceitas(server.conexao_aceita)
asyncio.get_event_loop().run_forever()

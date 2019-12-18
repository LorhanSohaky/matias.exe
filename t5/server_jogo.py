#!/usr/bin/env python3
# Este é um exemplo de um programa que faz eco, ou seja, envia de volta para
# o cliente tudo que for recebido em uma conexão.
import re
import json
import traceback
import random
from jogo.vars import rows
import asyncio
from camadafisica import ZyboSerialDriver
from mytcp import Servidor as Tcp  # copie o arquivo da Etapa 2
from myip import CamadaRede       # copie o arquivo da Etapa 3
from myslip import CamadaEnlace   # copie o arquivo da Etapa 4

DEBUG = True


MAX_FRUITS = 5
DELAY_ADD_FRUITS = 3


def move_left(current_position, next_position):
    next_x, _ = next_position
    current_x, current_y = current_position

    return (next_x, current_y) if current_x - 1 == next_x and next_x >= 0 \
        else (current_x, current_y)


def move_right(current_position, next_position):
    next_x, _ = next_position
    current_x, current_y = current_position

    return (next_x, current_y) if current_x + 1 == next_x and next_x < rows \
        else (current_x, current_y)


def move_up(current_position, next_position):
    _, next_y = next_position
    current_x, current_y = current_position

    return (current_x, next_y) if current_y - 1 == next_y and next_y >= 0 \
        else (current_x, current_y)


def move_down(current_position, next_position):
    _, next_y = next_position
    current_x, current_y = current_position

    return (current_x, next_y) if current_y + 1 == next_y and next_y < rows \
        else (current_x, current_y)


class Server:
    def __init__(self):
        self.players = []
        self.fruits = []

        self.loop = asyncio.get_event_loop()
        self.interval = DELAY_ADD_FRUITS
        self.timer = None
        self.add_fruits()

        if DEBUG:
            print('Iniciando servidor!')

    def dados_recebidos(self, conexao, dados):
        if DEBUG:
            print(conexao, 'recebido', dados)
        if dados == b'':
            if DEBUG:
                src_addr, src_port, _, _ = conexao.id_conexao
                print('Fechando conexão com', f'{src_addr}:{src_port}')
            player = self.get_player(conexao)
            self.players.remove(player)
            conexao.fechar()

        else:
            dados_decodificados = dados.decode()
            matches = re.finditer(r'\{.+?\}', dados_decodificados, re.MULTILINE)
            for matchNum, match in enumerate(matches, start=1):
                dados_decodificados = json.loads(match.group())
                self.parser(conexao, dados_decodificados)
                self.broadcast()

    def conexao_aceita(self, conexao):
        initial_state = {'id': conexao, 'position': (0, 0), 'score': 0}

        self.players.append(initial_state)
        conexao.registrar_recebedor(self.dados_recebidos)

        other_players = list(
            filter(lambda item: item['id'] != conexao,
                   self.players.copy()))

        other_players = list(
            map(lambda item: {'position': item['position'],
                              'score': item['score']}, other_players))
        state = {
            'players': other_players,
            'fruits': self.fruits,
            'me': {
                'position': initial_state['position'],
                'score': initial_state['score']
            }
        }

        msg = json.dumps(state) + '\n'

        conexao.enviar(msg.encode())

    def private_message(self, msg, conexao):
        msg_encoded = msg.encode()
        conexao.enviar(msg_encoded)

    def broadcast(self):

        for player in self.players:
            conexao = player['id']
            other_players = list(
                filter(lambda item: item['id'] != conexao,
                       self.players.copy()))

            other_players = list(
                map(lambda item: {'position': item['position'],
                                  'score': item['score']}, other_players))
            me = self.get_player(player['id'])
            state = {
                'players': other_players,
                'fruits': self.fruits,
                'me': {'position': me['position'], 'score': me['score']}
            }

            msg = json.dumps(state).encode() + b'\n'

            conexao.enviar(msg)

    def get_player(self, conexao):
        return list(filter(lambda item:
                           item['id'] == conexao, self.players))[0]

    def move(self, player, dados):
        current_position = player['position']
        next_position = dados['position']

        actions = {
            'move_left': move_left,
            'move_right': move_right,
            'move_up': move_up,
            'move_down': move_down,
        }

        try:
            position = actions[dados['action']](
                current_position, next_position)
            player['position'] = position
        except Exception:
            traceback.print_exc()

    def check_fruits(self, player):
        position = player['position']
        if position in self.fruits:
            player['score'] += 1
            self.fruits.remove(position)

    def add_fruits(self):
        self.timer = self.loop.call_later(
            self.interval, self.add_fruits)
        if len(self.fruits) < MAX_FRUITS:
            x = random.randrange(rows)
            y = random.randrange(rows)
            self.fruits.append((x, y))
            self.broadcast()

    def parser(self, conexao, dados):
        player = self.get_player(conexao)

        self.move(player, dados)
        self.check_fruits(player)


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
print('sudo ifconfig sl0 {} pointopoint {} mtu 1500'.format(
    outra_ponta, nossa_ponta))
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

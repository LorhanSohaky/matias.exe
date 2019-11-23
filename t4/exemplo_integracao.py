#!/usr/bin/env python3

# Note que não é mais necessário fazer a gambiarra com o iptables que era feita
# nas etapas anteriores, pois agora nosso código Python vai assumir o controle
# de TODAS as camadas da rede!

# Este é um exemplo de um programa que faz eco, ou seja, envia de volta para
# o cliente tudo que for recebido em uma conexão.

import asyncio
from camadafisica import PTY
from mytcp import Servidor   # copie o arquivo da Etapa 2
from myip import CamadaRede  # copie o arquivo da Etapa 3
from myslip import CamadaEnlace

def dados_recebidos(conexao, dados):
    if dados == b'':
        conexao.fechar()
    else:
        conexao.enviar(dados)   # envia de volta

def conexao_aceita(conexao):
    conexao.registrar_recebedor(dados_recebidos)   # usa esse mesmo recebedor para toda conexão aceita

linha_serial = PTY()
outra_ponta = '192.168.123.1'
nossa_ponta = '192.168.123.2'

print('Para conectar a outra ponta da camada física, execute:')
print('  sudo slattach -v -p slip {}'.format(linha_serial.pty_name))
print('  sudo ifconfig sl0 {} pointopoint {}'.format(outra_ponta, nossa_ponta))
print()
print('O serviço ficará acessível no endereço {}'.format(nossa_ponta))
print()

enlace = CamadaEnlace({outra_ponta: linha_serial})
rede = CamadaRede(enlace)
rede.definir_endereco_host(nossa_ponta)
rede.definir_tabela_encaminhamento([
    ('0.0.0.0/0', outra_ponta)
])
servidor = Servidor(rede, 7000)
servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)
asyncio.get_event_loop().run_forever()

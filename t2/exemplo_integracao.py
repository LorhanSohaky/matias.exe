#!/usr/bin/env python3
# Antes de usar, execute o seguinte comando para evitar que o Linux feche
# as conexões TCP que o seu programa estiver tratando:
#
# sudo iptables -I OUTPUT -p tcp --tcp-flags RST RST -j DROP


# Este é um exemplo de um programa que faz eco, ou seja, envia de volta para
# o cliente tudo que for recebido em uma conexão.

import asyncio
from camadarede import CamadaRedeLinux
from mytcp import Servidor

def dados_recebidos(conexao, dados):
    if dados == b'':
        conexao.fechar()
    else:
        conexao.enviar(dados)   # envia de volta

def conexao_aceita(conexao):
    conexao.registrar_recebedor(dados_recebidos)   # usa esse mesmo recebedor para toda conexão aceita

rede = CamadaRedeLinux()
servidor = Servidor(rede, 7000)
servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)
asyncio.get_event_loop().run_forever()

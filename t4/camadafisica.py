import os
import errno
import fcntl
import termios
import asyncio

class PTY:
    def __init__(self):
        pty, slave_fd = os.openpty()
        iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(pty)
        ispeed = termios.B115200
        ospeed = termios.B115200
        # cfmakeraw
        iflag &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK | termios.ISTRIP |
                   termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IXON)
        oflag &= ~termios.OPOST
        lflag &= ~(termios.ECHO | termios.ECHONL | termios.ICANON |
                   termios.ISIG | termios.IEXTEN)
        cflag &= ~(termios.CSIZE | termios.PARENB)
        cflag |= termios.CS8
        #
        termios.tcsetattr(pty, termios.TCSANOW, [iflag, oflag, cflag, lflag,
                                                 ispeed, ospeed, cc])
        fcntl.fcntl(pty, fcntl.F_SETFL, os.O_NONBLOCK)
        pty_name = os.ttyname(slave_fd)
        os.close(slave_fd)
        self.pty = pty
        self.pty_name = pty_name
        asyncio.get_event_loop().add_reader(pty, self.__raw_recv)

    def __raw_recv(self):
        try:
            dados = os.read(self.pty, 2048)
            if self.callback:
                self.callback(dados)
        except OSError as e:
            if e.errno == errno.EIO:
                pass      # a outra ponta está fechada
            else:
                raise e

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando vierem dados da linha serial
        """
        self.callback = callback

    def enviar(self, dados):
        """
        Envia dados para a linha serial
        """
        os.write(self.pty, dados)


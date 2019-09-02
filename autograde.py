#!/usr/bin/python3
import os
import signal
import json
import subprocess


def main():
    tests_weight = [1, 1, 2, 3, 2]
    scores = {}

    if os.path.exists('./compilar'):
        print('Chamando ./compilar')
        assert os.system('./compilar') == 0
    else:
        print('Arquivo "compilar" não existe, pulando compilação')

    for i, weight in enumerate(tests_weight):
        testno = i + 1
        pid = os.spawnlp(os.P_NOWAIT, './servidor', './servidor')
        print('\nServidor executando no pid=%d' % pid)

        test = 'test%d' % testno
        scores[test] = 0

        print('Teste #%d' % testno)
        timeout = 5
        p = subprocess.Popen('./%s.py' % test)
        try:
            if p.wait(timeout=timeout) == 0:
                scores[test] = weight
                print('OK')
        except subprocess.TimeoutExpired:
            print('%s: TIMEOUT (%.3f s)' % (test, timeout))
            p.kill()

        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)

    print(json.dumps({'scores':scores}))


if __name__ == '__main__':
    main()

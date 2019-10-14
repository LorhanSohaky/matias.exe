#!/usr/bin/env python3
import os
import signal
import json
import subprocess
import time


def main():
    tests_weight = [1, 1, 1, 1, 2, 2, 2]
    tests_timeout = [0.5, 0.5, 0.5, 0.5, 6, 5, 2]
    scores = {}
    assert sum(tests_weight) == 10

    for i, (weight, timeout) in enumerate(zip(tests_weight, tests_timeout)):
        testno = i + 1

        test = 'test%d' % testno
        scores[test] = 0

        print('Teste #%d' % testno)
        p = subprocess.Popen('./%s.py' % test)
        try:
            if p.wait(timeout=timeout) == 0:
                scores[test] = weight
                print('OK')
        except subprocess.TimeoutExpired:
            print('%s: TIMEOUT (%.3f s)' % (test, timeout))
            p.kill()

    print(json.dumps({'scores':scores}))


if __name__ == '__main__':
    main()

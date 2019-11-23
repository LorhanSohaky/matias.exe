#!/usr/bin/env python3
import json
import subprocess


def main():
    tests_weight = 4 * [2.5]
    tests_timeout = 4 * [0.5]
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

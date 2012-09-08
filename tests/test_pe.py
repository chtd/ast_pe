# -*- encoding: utf-8 -*-

import unittest

import ast_pe.partial


class Test(unittest.TestCase):
    def test(self):
       pass # TODO 


def stupid_power(n, x):
    if not isinstance(n, int) or n < 0:
        raise ValueError('Base should be a positive integer')
    else:
        v = 1
        for _ in xrange(n):
            v *= x
        return v

def smart_power(n, x):
    if n % 2 == 0:
        v = smart_power(n / 2, x)
        return v * v
    else:
        return x * smart_power(n - 1, x)


if __name__ == '__main__':
    unittest.main()

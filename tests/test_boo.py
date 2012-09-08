# -*- encoding: utf-8 -*-

import unittest

import ast_pe.partial


class TestBoo(unittest.TestCase):
    def test(self):
        self.assertEqual(ast_pe.partial.foo(), 'bar')


if __name__ == '__main__':
    unittest.main()

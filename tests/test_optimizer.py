# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import BaseTestCase
from ast_pe.optimizer import Optimizer


class TestOptimizer(BaseTestCase):
    def test_const_folding(self):
        def foo(n, m):
            a = n ** 2
            return a * n + (m - 2) * (n + 1)

        #def expected_foo(n



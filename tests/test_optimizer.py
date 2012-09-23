# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import BaseTestCase
from ast_pe.optimizer import Optimizer


class TestOptimizer(BaseTestCase):
    def test_constant_propagation(self):
        self._test_optization(
                'a * n + (m - 2) * (n + 1)', {'n': 5}, 
                'a * 5 + (m - 2) * (5 + 1)')
                
    def _test_optization(self, source, bindings, expected_source):
        ''' Test that with given bindings, Optimizer transforms
        source to expected_source
        '''
        self.assertASTEqual(
                Optimizer(bindings).visit(ast.parse(source)),
                ast.parse(expected_source))



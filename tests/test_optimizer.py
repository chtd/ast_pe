# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import BaseTestCase, shift_source
from ast_pe.optimizer import Optimizer


class TestOptimizer(BaseTestCase):
    def test_constant_propagation(self):
        self._test_optization(
                'a * n + (m - 2) * (n + 1)', dict(n=5),
                'a * 5 + (m - 2) * (5 + 1)')
        self._test_optization(
                'a * n + (m - 2) * (n + 1)', dict(n=5.0),
                'a * 5.0 + (m - 2) * (5.0 + 1)')
        self._test_optization(
                'foo[:5]', dict(foo="bar"),
                '"bar"[:5]')

    def test_constant_propagation_fail(self):
        ''' Test that constant propogation does not happen on primitive
        subclasses
        '''
        class Int(int): pass
        self._test_optization(
                'm * n', dict(m=Int(2)),
                'm * n')
        self._test_optization(
                'm * n', dict(m=Int(2), n=3),
                'm * 3')
        class Float(float): pass
        self._test_optization(
                'm * n', dict(m=Float(2.0)),
                'm * n')
        class String(str): pass
        self._test_optization(
                'm + n', dict(m=String('foo')),
                'm + n')
        class Unicode(unicode): pass
        self._test_optization(
                'm + n', dict(m=Unicode(u'foo')),
                'm + n')
    
    def test_if_true_elimination(self):
        true_values = [True, 1, 2.0, object(), "foo"]
        self.assertTrue(all(true_values))
        for x in true_values:
            self._test_optization(
                    'if x: print "x is True"', dict(x=x),
                    'print "x is True"')
        self._test_optization("""
            if x:
                do_stuff()
            else:
                do_other_stuff()
            """,
            dict(x=2),
            'do_stuff()')

    def _test_optization(self, source, bindings, expected_source):
        ''' Test that with given bindings, Optimizer transforms
        source to expected_source
        '''
        self.assertASTEqual(
                Optimizer(bindings).visit(ast.parse(shift_source(source))),
                ast.parse(shift_source(expected_source)))



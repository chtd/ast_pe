# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import BaseTestCase, shift_source
from ast_pe.optimizer import Optimizer


class BaseOptimizerTestCase(BaseTestCase):
    def _test_optization(self, source, bindings, expected_source):
        ''' Test that with given bindings, Optimizer transforms
        source to expected_source
        '''
        self.assertASTEqual(
                Optimizer(bindings).visit(ast.parse(shift_source(source))),
                ast.parse(shift_source(expected_source)))


class TestConstantPropagation(BaseOptimizerTestCase):
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

class TestIf(BaseOptimizerTestCase):
    def test_if_true_elimination(self):
        ''' Eliminate if test, if the value is known at compile time
        '''
        true_values = [True, 1, 2.0, object(), "foo"]
        self.assertTrue(all(true_values))
        for x in true_values:
            self._test_optization(
                    'if x: print "x is True"', dict(x=x),
                    'print "x is True"')
        self._test_optization('''
            if x:
                do_stuff()
            else:
                do_other_stuff()
            ''',
            dict(x=2),
            'do_stuff()')
    
    def test_if_no_elimination(self):
        ''' Test that there is no unneeded elimination of if test
        '''
        self._test_optization('''
            if x:
                do_stuff()
            else:
                do_other_stuff()
            ''',
            dict(y=2),
            '''
            if x:
                do_stuff()
            else:
                do_other_stuff()
            ''')

    def test_if_false_elimination(self):
        ''' Eliminate if test, when test is false
        '''
        class Falsy(object): 
            def __nonzero__(self):
                return False
        false_values = [0, '', [], {}, set(), False, None, Falsy()]
        for x in false_values:
            self._test_optization('''
                if x:
                    do_stuff()
                else:
                    do_other_stuff()
                ''',
                dict(x=x),
                'do_other_stuff()')

    def test_if_empty_elimination(self):
        ''' Eliminate if completly, when corresponding clause is empty
        '''
        self._test_optization('if x: do_stuff()', dict(x=False), 'pass')
        self._test_optization('''
                if x:
                    pass
                else:
                    do_stuff()
                ''', 
                dict(x=object()),
                'pass')



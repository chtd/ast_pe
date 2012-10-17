# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import BaseTestCase, shift_source, ast_to_string, \
        ast_to_source, fn_to_ast
from ast_pe.optimizer import optimized_ast
from ast_pe.decorators import pure_function, inline


class BaseOptimizerTestCase(BaseTestCase):
    def _test_opt(self, source, constants, expected_source=None,
            expected_new_bindings=None, print_source=False):
        ''' Test that with given constants, optimized_ast transforms
        source to expected_source.
        It :expected_new_bindings: is given, we check that they
        are among new bindings returned by optimizer.
        '''
        if print_source:
            print ast_to_string(ast.parse(shift_source(source)))
        if expected_source is None:
            expected_source = source
        ast_tree = ast.parse(shift_source(source))
        new_ast, bindings = optimized_ast(ast_tree, constants)
        self.assertASTEqual(new_ast, ast.parse(shift_source(expected_source)))
        if expected_new_bindings:
            for k in expected_new_bindings:
                if k not in bindings:
                    print 'bindings:', bindings
                self.assertEqual(bindings[k], expected_new_bindings[k])


class TestConstantPropagation(BaseOptimizerTestCase):
    def test_constant_propagation(self):
        self._test_opt(
                'a * n + (m - 2) * (n + 1)', dict(n=5),
                'a * 5 + (m - 2) * 6')
        self._test_opt(
                'a * n + (m - 2) * (n + 1)', dict(n=5.0),
                'a * 5.0 + (m - 2) * 6.0')
        self._test_opt(
                'foo[:5]', dict(foo="bar"),
                '"bar"[:5]')
        self._test_opt(
                'foo', dict(foo=False),
                'False')
        self._test_opt(
                'foo', dict(foo=True),
                'True')

    def test_constant_propagation_fail(self):
        ''' Test that constant propogation does not happen on primitive
        subclasses
        '''
        class Int(int): pass
        self._test_opt(
                'm * n', dict(m=Int(2)),
                'm * n')
        self._test_opt(
                'm * n', dict(m=Int(2), n=3),
                'm * 3')
        class Float(float): pass
        self._test_opt(
                'm * n', dict(m=Float(2.0)),
                'm * n')
        class String(str): pass
        self._test_opt(
                'm + n', dict(m=String('foo')),
                'm + n')
        class Unicode(unicode): pass
        self._test_opt(
                'm + n', dict(m=Unicode(u'foo')),
                'm + n')

class TestIf(BaseOptimizerTestCase):
    def test_if_true_elimination(self):
        ''' Eliminate if test, if the value is known at compile time
        '''
        true_values = [True, 1, 2.0, object(), "foo", int]
        self.assertTrue(all(true_values))
        for x in true_values:
            self._test_opt(
                    'if x: print "x is True"', dict(x=x),
                    'print "x is True"')
        self._test_opt('''
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
        self._test_opt('''
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
            self._test_opt('''
                if x:
                    do_stuff()
                else:
                    do_other_stuff()
                    if True:
                        do_someother_stuff()
                        and_more_stuff()
                ''',
                dict(x=x),
                '''
                do_other_stuff()
                do_someother_stuff()
                and_more_stuff()
                ''')

    def test_if_empty_elimination(self):
        ''' Eliminate if completly, when corresponding clause is empty
        '''
        self._test_opt('if x: do_stuff()', dict(x=False), 'pass')
        self._test_opt('''
                if x:
                    pass
                else:
                    do_stuff()
                ''', 
                dict(x=object()),
                'pass')
        
    def test_if_visit_only_true_branch(self):
        global_state = dict(cnt=0)
        
        @pure_function
        def inc():
            global_state['cnt'] += 1
            return True

        self._test_opt('if a: inc()', dict(a=False, inc=inc), 'pass')
        self.assertEqual(global_state['cnt'], 0)

        self._test_opt('''
                if a: 
                    dec()
                else:
                    inc()
                ''', dict(a=False, inc=inc), 'True')
        self.assertEqual(global_state['cnt'], 1)
    
    def test_visit_all_branches(self):
        self._test_opt('''
                if x > 0:
                    if True:
                        x += 1
                else:
                    if False:
                        return 0
                ''',
                dict(),
                '''
                if x > 0:
                    x += 1
                else:
                    pass
                ''')


class TestFnEvaluation(BaseOptimizerTestCase):
    ''' Test function calling
    '''
    def test_call_no_args(self):
        @pure_function
        def fn():
            return 'Hi!'
        self._test_opt('x = fn()', dict(fn=fn), 'x = "Hi!"')

    def test_call_with_args(self):
        @pure_function
        def fn(x, y):
            return x + [y]
        self._test_opt('z = fn(x, y)', dict(fn=fn, x=10), 'z = fn(10, y)')
        self._test_opt(
                'z = fn(x, y)',
                dict(fn=fn, x=[10], y=20.0),
                'z = __ast_pe_var_1',
                dict(__ast_pe_var_1=[10, 20.0]))

    def test_call_with_starargs(self):
        pass # TODO
    
    def test_call_with_kwargs(self):
        pass #TODO

    def test_exception(self):
        ''' Test when called function raises an exception - 
        we want it to raise it in specialized function 
        '''
        @pure_function
        def fn():
            return 1 / 0
        self._test_opt('x = fn()', dict(fn=fn), 'x = fn()')


class TestBuiltinsEvaluation(BaseOptimizerTestCase):
    ''' Test that we can evaluate builtins
    '''
    def test_evaluate(self):
        self._test_opt('isinstance(n, int)', dict(n=10), 'True')


class TestUnaryOp(BaseOptimizerTestCase):
    def test_not(self):
        self._test_opt('not x', dict(x="s"), 'False')
        self._test_opt('not x', dict(x=0), 'True')
        self._test_opt('not 1', dict(), 'False')
        self._test_opt('not False', dict(), 'True')


class TestBoolOp(BaseOptimizerTestCase):
    def test_and(self):
        self._test_opt('a and b', dict(a=False), 'False')
        self._test_opt('a and b', dict(a=True), 'b')
        self._test_opt(
                'a and b()', dict(a=True, b=pure_function(lambda: True)),
                'True')
        self._test_opt(
                'a and b and c and d', dict(a=True, c=True),
                'b and d')

    def test_and_short_circut(self):
        global_state = dict(cnt=0)

        @pure_function
        def inc():
            global_state['cnt'] += 1
            return True

        self._test_opt('a and inc()', dict(a=False, inc=inc), 'False')
        self.assertEqual(global_state['cnt'], 0)

        self._test_opt('a and inc()', dict(a=True, inc=inc), 'True')
        self.assertEqual(global_state['cnt'], 1)

    def test_or(self):
        self._test_opt('a or b', dict(a=False), 'b')
        self._test_opt('a or b', dict(a=True), 'True')
        self._test_opt('a or b', dict(a=False, b=False), 'False')
        self._test_opt(
                'a or b()', dict(a=False, b=pure_function(lambda: True)),
                'True')
        self._test_opt('a or b or c or d', dict(a=False, c=False), 'b or d')

    def test_or_short_circut(self):
        global_state = dict(cnt=0)

        @pure_function
        def inc():
            global_state['cnt'] += 1
            return True

        self._test_opt('a or inc()', dict(a=True, inc=inc), 'True')
        self.assertEqual(global_state['cnt'], 0)

        self._test_opt('a or inc()', dict(a=False, inc=inc), 'True')
        self.assertEqual(global_state['cnt'], 1)
    
    def test_mix(self):
        self._test_opt(
                '''
                if not isinstance(n, int) or n < 0:
                    foo()
                else:
                    bar()
                ''',
                dict(n=0),
                'bar()')


class Testcompare(BaseOptimizerTestCase):
    def test_eq(self):
        self._test_opt('0 == 0', {}, 'True')
        self._test_opt('0 == 1', {}, 'False')
        self._test_opt('a == b', dict(a=1), '1 == b')
        self._test_opt('a == b', dict(b=1), 'a == 1')
        self._test_opt('a == b', dict(a=1, b=1), 'True')
        self._test_opt('a == b', dict(a=2, b=1), 'False')
        self._test_opt(
                'a == b == c == d', dict(a=2, c=2), 
                '2 == b == 2 == d')

    def test_mix(self):
        self._test_opt('a < b >= c', dict(a=0, b=1, c=1), 'True')
        self._test_opt('a <= b > c', dict(a=0, b=1, c=1), 'False')


class TestRemoveDeadCode(BaseOptimizerTestCase):
    def test_remove_pass(self):
        self._test_opt(
                '''
                def fn(x):
                    x += 1
                    pass
                    return x
                ''',
                dict(),
                '''
                def fn(x):
                    x += 1
                    return x
                ''')

    def test_remove_pass_if(self):
        self._test_opt(
                '''
                if x > 0:
                    x += 1
                    pass
                ''',
                dict(),
                '''
                if x > 0:
                    x += 1
                ''')

    def test_not_remove_pass(self):
        self._test_opt(
                '''
                if x > 0:
                    pass
                ''',
                dict(),
                '''
                if x > 0:
                    pass
                ''')

    def test_remove_after_return(self):
        self._test_opt(
                '''
                def fn(x):
                    x += 1
                    return x
                    x += 1
                ''',
                dict(),
                '''
                def fn(x):
                    x += 1
                    return x
                ''')

    def test_remove_after_return_if(self):
        self._test_opt(
                '''
                if x > 0:
                    x += 1
                    return x
                    x += 1
                ''',
                dict(),
                '''
                if x > 0:
                    x += 1
                    return x
                ''')

class TestFunctional(BaseOptimizerTestCase):
    def test_if_on_stupid_power(self):
        source = '''
        def fn(x, n):
            if not isinstance(n, int) or n < 0:
                raise ValueError('Base should be a positive integer')
            else:
                if n == 0:
                    return 1
                if n == 1:
                    return x
                v = 1
                for _ in range(n):
                    v *= x
                return v
            '''
        self._test_opt(source, dict(n='foo'), '''
        def fn(x, n):
            raise ValueError('Base should be a positive integer')
            ''')
        self._test_opt(source, dict(n=0), '''
        def fn(x, n):
            return 1
            ''')
        self._test_opt(source, dict(n=1), '''
        def fn(x, n):
            return x
            ''')
        self._test_opt(source, dict(n=2), '''
        def fn(x, n):
            v = 1
            for _ in __ast_pe_var_1:
                v *= x
            return v
            ''',
            dict(__ast_pe_var_1=range(2)))


class TestSimpleMutation(BaseOptimizerTestCase):
    ''' Test that nodes whose values are known first but are mutated later
    are not substituted with values calculated at compile time.
    '''
    def test_self_mutation_via_method(self):
        self._test_opt(
                '''
                if x:
                    bar()
                ''',
                dict(x=object()),
                'bar()')
        self._test_opt(
                '''
                x.foo()
                if x:
                    bar()
                ''',
                dict(x=object()))
    
    def test_mutation_of_fn_args(self):
        self._test_opt(
                '''
                if x:
                    bar()
                ''',
                dict(x=object()),
                'bar()')
        self._test_opt(
                '''
                foo(x)
                if x:
                    bar()
                ''',
                dict(x=object()))

    def test_leave_fn(self):
        pass # TODO


class TestBinaryArithmetic(BaseOptimizerTestCase):
    def test_opt(self):
        self._test_opt('1 + 1', {}, '2')
        self._test_opt('1 + (1 * 67.0)', {}, '68.0')
        self._test_opt('1 / 2', {}, '0')
        self._test_opt('1 / 2.0', {}, '0.5')
        self._test_opt('3 % 2', {}, '1')
        self._test_opt('x / y', dict(x=1, y=2.0), '0.5')

    def test_no_opt(self):
        class NaN(object):
            def __init__(self, value):
                self.value = value
            def __add__(self, other):
                return NaN(self.value - other.value)
        self._test_opt('x + y', dict(x=NaN(1), y=NaN(2)))


class TestInlining(BaseOptimizerTestCase):
    ''' Test simple inlining
    '''
    def test_simple_return(self):
        @inline
        def inlined(y):
            l = []
            for _ in xrange(y):
                l.append(y.do_stuff())
            return l
        self._test_opt(
                '''
                def outer(x):
                    a = x.foo()
                    if a:
                        b = a * 10
                    a = b + inlined(x)
                    return a
                ''',
                dict(inlined=inlined),
                '''
                def outer(x):
                    a = x.foo()
                    if a:
                        b = a * 10
                    __ast_pe_var_1 = x
                    __ast_pe_var_2 = []
                    for __ast_pe_var_3 in xrange(__ast_pe_var_1):
                        __ast_pe_var_2.append(__ast_pe_var_1.do_stuff())
                    __ast_pe_var_4 = __ast_pe_var_2
                    a = b + __ast_pe_var_4
                    return a
                ''')

    def test_complex_return(self):
        @inline
        def inlined(y):
            l = []
            for i in iter(y):
                l.append(i.do_stuff())
            if l:
                return l
            else:
                return None
        self._test_opt(
                '''
                def outer(x):
                    a = x.foo()
                    if a:
                        b = a * 10
                        a = inlined(x - 3) + b
                    return a
                ''',
                dict(inlined=inlined),
                '''
                def outer(x):
                    a = x.foo()
                    if a:
                        b = a * 10
                        __ast_pe_var_1 = x - 3
                        __ast_pe_var_5 = True
                        while __ast_pe_var_5:
                            __ast_pe_var_5 = False
                            __ast_pe_var_2 = []
                            for __ast_pe_var_3 in iter(__ast_pe_var_1):
                                __ast_pe_var_2.append(__ast_pe_var_3.do_stuff())
                            if __ast_pe_var_2:
                                __ast_pe_var_4 = __ast_pe_var_2
                                break
                            else:
                                __ast_pe_var_4 = None
                                break
                        a = __ast_pe_var_4 + b
                    return a
                '''
                )


class TestRecursionInlining(BaseOptimizerTestCase):
    ''' Recursion inlining test
    '''
    def test_no_inlining(self):
        self._test_opt(
                '''
                def power(x, n):
                    if n == 0:
                        return 1
                    elif n % 2 == 0:
                        v = power(x, n / 2)
                        return v * v
                    else:
                        return x * power(x, n - 1)
                ''',
                dict(n=1),
                '''
                def power(x, n):
                    return x * power(x, 0)
                ''')

    def test_inlining(self):
        @inline 
        def power(x, n):
            if n == 0:
                return 1
            elif n % 2 == 0:
                v = power(x, n / 2)
                return v * v
            else:
                return x * power(x, n - 1)
        self._test_opt(
                '''
                def power(x, n):
                    if n == 0:
                        return 1
                    elif n % 2 == 0:
                        v = power(x, n / 2)
                        return v * v
                    else:
                        return x * power(x, n - 1)
                ''',
                dict(n=1, power=power),
                '''
                def power(x, n):
                    return x * 1
                ''')


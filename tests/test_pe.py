# -*- encoding: utf-8 -*-

import unittest
import functools
from collections import Iterable

from ast_pe.utils import get_ast, eq_ast
from ast_pe.partial import specialized_ast, specialized_fn


class TestCase(unittest.TestCase):
    def test_if_on_stupid_power(self):
        kwargs_list = [{'x': v} for v in [0, 1, 0.01, 5e10]]
        for fn in (stupid_power_foo, 
                stupid_power_0, stupid_power_1, stupid_power_2):
            self._test_partial_ast(stupid_power, fn)
            self._test_partial_fn(stupid_power, fn, kwargs_list)

    def _test_partial_ast(self, base_fn, partial_fn):
        ''' Check that partial evaluations of base_fn with args taken
        from partial_fn.__doc__ gives the same AST as partial_fn
        '''
        partial_kwargs = eval(partial_fn.__doc__) 
        partial_ast = specialized_ast(base_fn, **partial_kwargs)
        expected_ast = get_ast(partial_fn)
        self.assertTrue(eq_ast(partial_ast, expected_ast))

    def _test_partial_fn(self, base_fn, partial_fn, kwargs_list):
        ''' Check that partial evaluation of base_fn with partial_args
        gives the same result on args_list
        as functools.partial(base_fn, partial_args), and partial_fn
        '''
        partial_kwargs = eval(partial_fn.__doc__)
        fn = specialized_fn(base_fn, **partial_kwargs)
        for kw in kwargs_list:
            self.assertFuncEqualOn(
                    functools.partial(base_fn, **partial_kwargs),
                    partial_fn, 
                    **kw)
            self.assertFuncEqualOn(
                    functools.partial(base_fn, **partial_kwargs),
                    fn,
                    **kw)

    def assertFuncEqualOn(self, fn1, fn2, *args, **kwargs):
        ''' Check that functions are the same, or raise the same exception
        '''
        v1 = v2 = e1 = e2 = None
        try: v1 = fn1(*args, **kwargs)
        except Exception as e1: pass
        try: v2 = fn2(*args, **kwargs)
        except Exception as e2: pass
        if e1 or e2:
            # reraise exception, if there is only one
            if e1 is None: fn2(*args, **kwargs)
            if e2 is None: fn1(*args, **kwargs)
            if type(e1) != type(e2):
                # assume that fn1 is more correct, so raise exception from fn2
                fn2(*args, **kwargs)
            self.assertEqual(type(e1), type(e2))
            self.assertEqual(e1.message, e2.message)
        else:
            self.assertIsNone(e1)
            self.assertIsNone(e2)
            self.assertEqual(v1, v2)


#=======================================================


def stupid_power(n, x):
    if not isinstance(n, int) or n < 0:
        raise ValueError('Base should be a positive integer')
    else:
        if n == 0:
            return 1
        if n == 1:
            return x
        v = 1
        for _ in xrange(n):
            v *= x
        return v


def stupid_power_foo(x):
    '{"n": "foo"}'
    raise ValueError('Base should be a positive integer')


def stupid_power_0(x):
    '{"n": 0}'
    return 1


def stupid_power_1(x):
    '{"n": 1}'
    return x


def stupid_power_2(x):
    '{"n": 2}'
    v = 1
    for _ in xrange(2):
        v *= x
    return v


#=======================================================


def smart_power(n, x):
    if n % 2 == 0:
        v = smart_power(n / 2, x)
        return v * v
    else:
        return x * smart_power(n - 1, x)


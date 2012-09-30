# -*- encoding: utf-8 -*-

import functools

from ast_pe.utils import BaseTestCase, fn_to_ast
from ast_pe.specializer import specialized_ast, specialized_fn


class TestSpecializer(BaseTestCase):
    def test_args_handling(self):
        def args_kwargs(a, b, c=None):
            return 1.0 * a / b * (c or 3)
        self.assertEqual(specialized_fn(args_kwargs, 1)(2),
                1.0 / 2 * 3)
        self.assertEqual(specialized_fn(args_kwargs, 1, 2, 1)(),
                1.0 / 2 * 1)

    def test_kwargs_handling(self):
        def args_kwargs(a, b, c=None):
            return 1.0 * a / b * (c or 3)
        self.assertEqual(specialized_fn(args_kwargs, c=4)(1, 2),
                1.0 / 2 * 4)
        self.assertEqual(specialized_fn(args_kwargs, 2, c=4)(6),
                2.0 / 6 * 4)
    
    def test_const_arg_substitution(self):
        def const_arg_substitution(n, m):
            return n + m
        def const_arg_substitution_1(m):
            '{"n": 1}'
            return 1 + m
        self._test_partial_ast(
                const_arg_substitution, const_arg_substitution_1)

    def test_if_on_stupid_power(self):
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
        kwargs_list = [{'x': v} for v in [0, 1, 0.01, 5e10]]
        for fn in (stupid_power_foo, 
                stupid_power_0, stupid_power_1, stupid_power_2):
            self._test_partial_ast(stupid_power, fn)
            self._test_partial_fn(stupid_power, fn, kwargs_list)

    # Utility methods

    def _test_partial_ast(self, base_fn, partial_fn):
        ''' Check that partial evaluations of base_fn with args taken
        from partial_fn.__doc__ gives the same AST as partial_fn
        '''
        partial_kwargs = eval(partial_fn.__doc__)
        partial_ast, _ = specialized_ast(fn_to_ast(base_fn), **partial_kwargs)
        expected_ast = fn_to_ast(partial_fn)
        expected_ast.body[0].name = base_fn.__name__ # rename fn
        del expected_ast.body[0].body[0] # remove __doc__
        self.assertASTEqual(partial_ast, expected_ast)

    def _test_partial_fn(self, base_fn, partial_fn, kwargs_list):
        ''' Check that partial evaluation of base_fn with partial_args
        gives the same result on args_list
        as functools.partial(base_fn, partial_args), and partial_fn
        '''
        partial_kwargs = eval(partial_fn.__doc__)
        fn = specialized_fn(base_fn, **partial_kwargs)
        for kw in kwargs_list:
            for f in (fn, partial_fn):
                for _ in xrange(2):
                    self.assertFuncEqualOn(
                            functools.partial(base_fn, **partial_kwargs),
                            f, **kw)

    def assertFuncEqualOn(self, fn1, fn2, *args, **kwargs):
        ''' Check that functions are the same, or raise the same exception
        '''
        v1 = v2 = e1 = e2 = None
        try: 
            v1 = fn1(*args, **kwargs)
        except Exception as e1:
            pass
        try:
            v2 = fn2(*args, **kwargs)
        except Exception as e2:
            pass
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


def smart_power(n, x):
    if not isinstance(n, int) or n < 0:
        raise ValueError('Base should be a positive integer')
    elif n == 0:
        return 1
    elif n % 2 == 0:
        v = smart_power(n / 2, x)
        return v * v
    else:
        return x * smart_power(n - 1, x)


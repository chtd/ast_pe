# -*- encoding: utf-8 -*-

import functools

from ast_pe.utils import BaseTestCase
from ast_pe.specializer import specialized_fn
from ast_pe.decorators import inline


class TestSpecializer(BaseTestCase):
    def test_args_handling(self):
        def args_kwargs(a, b, c=None):
            return 1.0 * a / b * (c or 3)
        self.assertEqual(
                specialized_fn(args_kwargs, globals(), locals(), 1)(2),
                1.0 / 2 * 3)
        self.assertEqual(
                specialized_fn(args_kwargs, globals(), locals(), 1, 2, 1)(),
                1.0 / 2 * 1)

    def test_kwargs_handling(self):
        def args_kwargs(a, b, c=None):
            return 1.0 * a / b * (c or 3)
        self.assertEqual(
                specialized_fn(args_kwargs, globals(), locals(), c=4)(1, 2),
                1.0 / 2 * 4)
        self.assertEqual(
                specialized_fn(args_kwargs, globals(), locals(), 2, c=4)(6),
                2.0 / 6 * 4)

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
        for n in ('foo', 0, 1, 2, 3):
            for x in [0, 1, 0.01, 5e10]:
                self._test_partial_fn(stupid_power, globals(), locals(),
                        lambda : dict(n=n), lambda : {'x': x })
    
    def test_if_on_recursive_power(self):
        @inline
        def power(n, x):
            if not isinstance(n, int) or n < 0:
                raise ValueError('Base should be a positive integer')
            elif n == 0:
                return 1
            elif n % 2 == 0:
                v = power(x, n / 2)
                return v * v
            else:
                return x * power(x, n - 1)
        for n in ('foo', 0, 1, 2, 3):
            for x in [0, 1, 0.01, 5e10]:
                self._test_partial_fn(power, globals(), locals(),
                        lambda : dict(n=n), lambda : {'x': x })

    def test_mutation_via_method(self):
        def mutty(x, y):
            x.append('foo')
            return x + [y]
        self._test_partial_fn(mutty, globals(), locals(),
                lambda : dict(x=[1]), lambda : {'y': 2 })

    # Utility methods

    def _test_partial_fn(self, base_fn, globals_, locals_,
            get_partial_kwargs, get_kwargs):
        ''' Check that partial evaluation of base_fn with partial_args
        gives the same result on args_list
        as functools.partial(base_fn, partial_args)
        '''
        fn = specialized_fn(base_fn, globals_, locals_, **get_partial_kwargs())
        partial_fn = functools.partial(base_fn, **get_partial_kwargs())
        # call two times to check for possible side-effects
        self.assertFuncEqualOn(partial_fn, fn, **get_kwargs()) # first
        self.assertFuncEqualOn(partial_fn, fn, **get_kwargs()) # second

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


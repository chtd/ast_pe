Partial evaluation on AST level
===============================

This library allows you perform code specialization at run-time,
turning this::

    def power(x, n):
        if n == 0:
            return 1
        elif n % 2 == 0:
            v = power(x, n / 2)
            return v * v
        else:
            return x * power(x, n - 1)

into this (given that n equals e.g. 27)::

    def power_27(x):
        _pow_2 = x * x
        _pow_3 = _pow_2 * x
        _pow_6 = _pow_3 * _pow_3
        _pow_12 = _pow_6 * _pow_6
        _pow_13 = _pow_12 * x
        _pow_26 = _pow_13 * _pow_13
        _pow_27 = _pow_26 * x
        return _pow_27

(**FIXME** - well, not quite yet)
that runs 10 time faster under CPython. 

Generaly partial evaluation
is beneficial if inputs of some function (or a set of functions, or methods)
can be decomposed into *static* (seldom changing) and *dynamic*. Than we
create specialied version of the algorithm for each encoutered static input,
and use it to process dynamic input. For example, for an interpreter
*static input* is the program, and *dynamic input* is the input to that program.
Partial evaluation turns interpreter into a compiler, which runs much faster.

The API is very simple, almost identical to ``functools.partial``::

    power_27 = specialized_fn(power, n=27)

Under the hood the library simplifies AST by performing usual
compiler optimizations, using known variable values:

* constant propagation
* constant folding
* dead-code elimination
* loop unrolling 
* function inlining

But here this optimizations can really make a difference, because
your function can heavily depend on a known at specialization input,
and so specialized function might have quite a different control flow,
as in the ``power(x, n)`` example.

In order to allow function inlining, you have to mark it as pure 
(having no side-effects) using ``pure_fn`` decorator. 
Variable mutation and assigment is handled gracefully (**FIXME** not yet).

Tests
-----

Run test with `nose <http://nose.readthedocs.org/en/latest/>`_::

    nosetests

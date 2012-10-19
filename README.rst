===============================
Partial evaluation on AST level
===============================

This library allows you perform code specialization at run-time,
turning this::

    @inline
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

that runs 10 time faster under CPython (variable names changed
to increase readability).

Generaly, partial evaluation
is beneficial if inputs of some function (or a set of functions, or methods)
can be decomposed into *static* (seldom changing) and *dynamic*. Than we
create specialied version of the algorithm for each encoutered static input,
and use it to process dynamic input. For example, for an interpreter
*static input* is the program, and *dynamic input* is the input to that program.
Partial evaluation turns interpreter into a compiler, which runs much faster.

The API is almost identical to ``functools.partial``::
    
    import ast_pe
    power_27 = ast_pe.specialized_fn(power, globals(), locals(), n=27)

You have to pass globals and locals right now, so the specializer
knowns the environment where specialized function was defined.

You must mark functions that you want inlined (maybe recursively)
with ``ast_pe.decorators.inline``. If some function or methods
operates on your static input, you can benefit from marking it as pure
using ``ast_pe.decorators.pure_fn`` (if it is really pure).

**TODO**
Or you can make the library make all the bookkeeping for you, creating
specialized versions and using them as meeded by the following decorator::
    
    @ast_pe.specialize_on('n', globals(), locals())
    def power(x, n):
        ...

But in this case the arguments we specialize on must be hashable. It they
are not, you will have to dispatch to specialized function yourself.

Under the hood the library simplifies AST by performing usual
compiler optimizations, using known variable values:

* constant propagation
* constant folding
* dead-code elimination
* loop unrolling (**TODO** - not yet)
* function inlining

But here this optimizations can really make a difference, because
your function can heavily depend on a known at specialization input,
and so specialized function might have quite a different control flow,
as in the ``power(x, n)`` example.

Variable mutation and assigment is handled gracefully (**TODO** 
right now only in the simplest cases).

Tests
=====

Run test with `nose <http://nose.readthedocs.org/en/latest/>`_::

    nosetests

Run specific test with::

    nosetests tests.test_optimizer:TestIf.test_if_visit_only_true_branch

Internals
=========

Mutation and variable assigment
-------------------------------

There are several cases when initially known variable can be changed, 
and we can no longer assume it is known.

Variable assigment::
   
    @specialize_on('n')
    def fn(n, x):
        n += x  # here n is no longer known

Variable mutation (is ``some_method`` is not declared as pure_fn, we can not
assume that it does not mutate ``foo``)::

    @specialize_on('foo')
    def fn(foo, x):
        foo.some_method() 

It can become more complex if other variables are envolved::

    @specialize_on('foo')
    def fn(foo, x):
        a = foo.some_pure_method()
        a.some_method()

Here not only we can not assume ``a`` to be constant, but the call to
``some_method`` could have mutated ``a``, that can hold a reference to
``foo`` or some part of it, so that mutating ``a`` changes ``foo`` too.

Another case that needs to be handled is variable escaping from 
the function via return statement (usually indirectly)::


    @specialize_on('foo')
    def fn(foo, x):
        a = foo.some_pure_method()
        return a

Here we have no garanty that ``a`` wont be mutated by the called of ``fn``,
so we can not compute ``foo.some_pure_method()`` once - we need a fresh
copy every time ``fn`` is called to preserve semantics.

To handle it in a sane way:

* we need to know the data flow inside the function - how variables
  depend on each other
* we need to know which variables might be mutated, and propagete this 
  information up the data flow
* we need to do the same for variables that leave the function
* we need to know which variables are rebound via assigment, and mark them
  as not being constant


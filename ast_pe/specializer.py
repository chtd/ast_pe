# -*- encoding: utf-8 -*-

from ast_pe.utils import fn_to_ast, eval_ast
from ast_pe.optimizer import Optimizer
from ast_pe.dataflow import DataFlowAnalyzer


def specialized_fn(fn, *args, **kwargs):
    ''' Return specialized version of fn, fixing given args and kwargs,
    just as functools.partial does, but specialized function should be faster
    '''
    # FIXME - grab globals from the module where it is defined
    fn_ast = fn_to_ast(fn)
    specialized_tree, bindings = specialized_ast(fn_ast, *args, **kwargs)
    return eval_ast(specialized_tree, globals_=bindings) 


def specialized_ast(fn_ast, *args, **kwargs):
    ''' Return AST of specialized function, and dict with closure bindings.
    args and kwargs have the same meaning as in functools.partial.
    Here we just handle the args and kwargs of function defenition.
    '''
    constants = {}
    fn_args = fn_ast.body[0].args
    assert not fn_args.vararg and not fn_args.kwarg # TODO
    if args:
        for arg, value in zip(fn_args.args[:len(args)], args):
            constants[arg.id] = value
        del fn_args.args[:len(args)]
    if kwargs:
        arg_by_id = dict((arg.id, arg) for arg in fn_args.args)
        for kwarg_name, kwarg_value in kwargs.iteritems():
            constants[kwarg_name] = kwarg_value
            fn_args.args.remove(arg_by_id[kwarg_name])
    dataflow_analyzer = DataFlowAnalyzer()
    dataflow_analyzer.visit(fn_ast)
    optimizer = Optimizer(constants, dataflow_analyzer.data_flow)
    return optimizer.visit(fn_ast), optimizer.constants



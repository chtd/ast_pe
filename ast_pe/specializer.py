# -*- encoding: utf-8 -*-

import ast
import numbers

from ast_pe.utils import get_ast, eval_ast


def specialized_fn(fn, *args, **kwargs):
    ''' Return specialized version of fn, fixing given args and kwargs,
    just as functools.partial does, but specialized function should be faster
    '''
    # FIXME - grab globals from the module where it is defined
    specialized_tree, bindings = specialized_ast(fn, *args, **kwargs)
    return eval_ast(specialized_tree, globals_=bindings) 


def specialized_ast(fn, *args, **kwargs):
    ''' Return AST of specialized function, and dict with closure bindings
    '''
    bindings = {}
    tree = get_ast(fn)
    fn_args = tree.body[0].args
    assert not fn_args.vararg and not fn_args.kwarg # TODO
    if args:
        for arg, value in zip(fn_args.args[:len(args)], args):
            bindings[arg.id] = value
        del fn_args.args[:len(args)]
    if kwargs:
        arg_by_id = dict((arg.id, arg) for arg in fn_args.args)
        for kwarg_name, kwarg_value in kwargs.iteritems():
            bindings[kwarg_name] = kwarg_value
            fn_args.args.remove(arg_by_id[kwarg_name])
    return PartialEvaluator(bindings, *args, **kwargs).visit(tree), bindings


class PartialEvaluator(ast.NodeTransformer):
    def __init__(self, bindings, *args, **kwargs):
        self.bindings = bindings
        self.args = args
        self.kwargs = kwargs
        super(PartialEvaluator, self).__init__()
    
    def visit_Name(self, node):
        self.generic_visit(node)
        if node.id in self.bindings:
            value = self.bindings[node.id]
            if isinstance(value, numbers.Number):
                return ast.Num(value, 
                        lineno=node.lineno, col_offset=node.col_offset)
            else:
                pass # TODO
        return node

    """
    def visit_If(self, node):
        self.generic_visit(node)
        if isinstance(node.test, ast.Compare):
            # pass if isinstance
        #import pdb; pdb.set_trace()
        print
        print 'visit_If', ast.dump(node)
        print
        return node
    """


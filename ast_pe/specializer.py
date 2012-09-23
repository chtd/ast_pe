# -*- encoding: utf-8 -*-

import ast
import numbers

from meta import asttools

from ast_pe.utils import get_ast, eval_ast, str_ast


def specialized_fn(fn, *args, **kwargs):
    ''' Return specialized version of fn, fixing given args and kwargs,
    just as functools.partial does, but specialized function should be faster
    '''
    # FIXME - grab globals from the module where it is defined
    specialized_tree, bindings = specialized_ast(fn, *args, **kwargs)
    return eval_ast(specialized_tree, globals_=bindings) 


def specialized_ast(fn, *args, **kwargs):
    ''' Return AST of specialized function, and dict with closure bindings.
    args and kwargs have the same meaning as in functools.partial.
    Here we just handle the args and kwargs of function defenition.
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
    return PartialEvaluator(bindings).visit(tree), bindings


class PartialEvaluator(ast.NodeTransformer):
    def __init__(self, bindings):
        ''' 
        bindings is a dict names-> values of variables known at compile time,
        that is populated with newly bound variables (results of calculations
        done at compile time)
        '''
        self.bindings = bindings
        super(PartialEvaluator, self).__init__()
    
    # TODO - handle variable mutation and assignment, 
    # to kick things from bindings

    def visit_Name(self, node):
        self.generic_visit(node)
        print 'visit_Name', self.bindings
        print str_ast(node)
        if isinstance(node.ctx, ast.Load) and node.id in self.bindings:
            value = self.bindings[node.id]
            if isinstance(value, numbers.Number):
                print 'substitute with number', value
                return ast.Num(value, 
                        lineno=node.lineno, col_offset=node.col_offset)
            elif isinstance(value, basestring):
                print 'substitute with string', value
                return ast.Str(value,
                        lineno=node.lineno, col_offset=node.col_offset)
            else:
                pass # TODO
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        print 'visit_If'
        print str_ast(node)
        test_symbols = asttools.get_symbols(node.test)
        # TODO - check if we can evaluate it with meta.asttols.get_symbols
        #import pdb; pdb.set_trace()
        #if isinstance(node.test, ast.Compare):
            # pass if isinstance
        return node


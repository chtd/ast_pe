# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import get_ast, eval_ast


def specialized_fn(fn, *args, **kwargs):
    ''' Return specialized version of fn, fixing given args and kwargs,
    just as functools.partial does, but specialized function should be faster
    '''
    specialized_tree = specialized_ast(fn, *args, **kwargs)
    return eval_ast(specialized_tree) 


def specialized_ast(fn, *args, **kwargs):
    tree = get_ast(fn)
    return PartialEvaluator(*args, **kwargs).visit(tree)


class PartialEvaluator(ast.NodeTransformer):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        super(PartialEvaluator, self).__init__()

    def generic_visit(self, node):
        return node

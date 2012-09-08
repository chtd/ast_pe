# -*- encoding: utf-8 -*-

import ast
import inspect


def get_ast(fn):
    ''' Return AST tree, parsed from fn
    '''
    return ast.parse(inspect.getsource(fn))


def eval_ast(tree):
    ''' Evaluate AST tree, which sould contain only one root node
    '''
    assert isinstance(tree, ast.Module) and len(tree.body) == 1
    code_object = compile(tree, '<nofile>', 'exec')
    eval(code_object)
    return locals()[tree.body[0].name]


def ast_equal(tree1, tree2):
    ''' Returns whether AST tree1 is equal to tree2 '''
    return ast.dump(tree1) == ast.dump(tree2)


# -*- encoding: utf-8 -*-

import re
import ast
import inspect

import meta.asttools


def get_ast(fn):
    ''' Return AST tree, parsed from fn
    '''
    source = inspect.getsource(fn)
    # FIXME - more general solution, here just a quick hack for tests
    if source.startswith(' '):
        n_spaces = len(re.match('^([ ]+)', source).group(0))
        source = '\n'.join(line[n_spaces:] for line in source.split('\n'))
    return ast.parse(source)


def eval_ast(tree, globals_=None):
    ''' Evaluate AST tree, which sould contain only one root node
    '''
    assert isinstance(tree, ast.Module) and len(tree.body) == 1
    code_object = compile(tree, '<nofile>', 'exec')
    locals_ = {}
    eval(code_object, globals_, locals_)
    return locals_[tree.body[0].name]


def eq_ast(tree1, tree2):
    ''' Returns whether AST tree1 is equal to tree2 
    '''
    return ast.dump(tree1) == ast.dump(tree2)


def get_source(tree):
    ''' Return python source of AST tree, as a string.
    '''
    return meta.asttools.dump_python_source(tree)


def str_ast(tree):
    ''' Return pretty-printed AST, as a string.
    '''
    return meta.asttools.str_ast(tree)


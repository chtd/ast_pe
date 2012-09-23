# -*- encoding: utf-8 -*-

import re
import sys
import ast
import inspect
import unittest

import meta.asttools


def fn_to_ast(fn):
    ''' Return AST tree, parsed from fn
    '''
    source = shift_source(inspect.getsource(fn))
    # FIXME - more general solution, here just a quick hack for tests
    return ast.parse(source)


def shift_source(source):
    ''' Shift source to the left - so that it starts with zero indentation
    '''
    source = source.rstrip()
    if source.startswith('\n'):
        source = source.lstrip('\n')
    if source.startswith(' '):
        n_spaces = len(re.match('^([ ]+)', source).group(0))
        source = '\n'.join(line[n_spaces:] for line in source.split('\n'))
    return source



def eval_ast(tree, globals_=None):
    ''' Evaluate AST tree, which sould contain only one root node
    '''
    assert isinstance(tree, ast.Module) and len(tree.body) == 1
    code_object = compile(tree, '<nofile>', 'exec')
    locals_ = {}
    eval(code_object, globals_, locals_)
    return locals_[tree.body[0].name]


def ast_equal(tree1, tree2):
    ''' Returns whether AST tree1 is equal to tree2 
    '''
    return ast.dump(tree1) == ast.dump(tree2)


def ast_to_source(tree):
    ''' Return python source of AST tree, as a string.
    '''
    return meta.asttools.dump_python_source(tree)


def ast_to_string(tree):
    ''' Return pretty-printed AST, as a string.
    '''
    return meta.asttools.str_ast(tree)


class BaseTestCase(unittest.TestCase):
    def assertASTEqual(self, test_ast, expected_ast):
        ''' Check that test_ast is equal to expected_ast, 
        printing helpful error message if they are not equal
        '''
        dump1, dump2 = ast.dump(test_ast), ast.dump(expected_ast)
        if dump1 != dump2:
            print >> sys.stderr, \
                    '\nexpected:\n{expected_ast}\n'\
                    '\ngot:\n{test_ast}\n'.format(
                            expected_ast=ast_to_source(expected_ast),
                            test_ast=ast_to_source(test_ast))
        self.assertEqual(dump1, dump2)

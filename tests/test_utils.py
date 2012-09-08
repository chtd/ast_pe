# -*- encoding: utf-8 -*-

import ast
from ast import Module, FunctionDef, arguments, Name, Param, If, Compare, \
        Return, BinOp, Load, Add, Subscript, Index, Str, Eq
import unittest

import ast_pe.utils


class TestCase(unittest.TestCase):
    def test_get_ast(self):
        tree = ast_pe.utils.get_ast(sample_fn)
        tree_dump = ast.dump(tree, annotate_fields=False)
        self.assertEqual(tree_dump, 
                "Module([FunctionDef('sample_fn', "
                "arguments([Name('x', Param()), Name('y', Param()), "
                "Name('foo', Param())], None, 'kw', [Str('bar')]), "
                "[If(Compare(Name('foo', Load()), [Eq()], [Str('bar')]), "
                "[Return(BinOp(Name('x', Load()), Add(), Name('y', Load())))], "
                "[Return(Subscript(Name('kw', Load()), "
                "Index(Str('zzz')), Load()))])], [])])")

    def test_compare_ast(self):
        tree = ast_pe.utils.get_ast(sample_fn)
        expected_tree = Module([FunctionDef('sample_fn', 
            arguments([Name('x', Param()), Name('y', Param()), 
                Name('foo', Param())], None, 'kw', [Str('bar')]), 
            [If(Compare(Name('foo', Load()), [Eq()], [Str('bar')]), 
                [Return(BinOp(Name('x', Load()), Add(), Name('y', Load())))], 
                [Return(Subscript(Name('kw', Load()), 
                    Index(Str('zzz')), Load()))])], [])])
        self.assertTrue(ast_pe.utils.ast_equal(tree, expected_tree))
        self.assertFalse(ast_pe.utils.ast_equal(
            tree, ast_pe.utils.get_ast(sample_fn2)))
        self.assertFalse(ast_pe.utils.ast_equal(
            tree, ast_pe.utils.get_ast(sample_fn3)))

    def test_compile_ast(self):
        tree = ast_pe.utils.get_ast(sample_fn)
        compiled_fn = ast_pe.utils.eval_ast(tree)
        self.assertEqual(compiled_fn(3, -9), sample_fn(3, -9))
        self.assertEqual(
                compiled_fn(3, -9, 'z', zzz=map), 
                sample_fn(3, -9, 'z', zzz=map))
    

def sample_fn(x, y, foo='bar', **kw):
    if foo == 'bar':
        return x + y
    else:
        return kw['zzz']


def sample_fn2(x, y, foo='bar', **kw):
    if foo == 'bar':
        return x - y
    else:
        return kw['zzz']


def sample_fn3(x, y, foo='bar', **kwargs):
    if foo == 'bar':
        return x + y
    else:
        return kwargs['zzz']


if __name__ == '__main__':
    unittest.main()

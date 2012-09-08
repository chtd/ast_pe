# -*- encoding: utf-8 -*-

import ast
import unittest

import ast_pe.utils
import ast_pe.astpretty


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
        compiled_fn = ast_pe.utils.eval_ast(tree)
        self.assertEqual(compiled_fn(3, -9), sample_fn(3, -9))
        self.assertEqual(
                compiled_fn(3, -9, 'z', zzz=map), 
                sample_fn(3, -9, 'z', zzz=map))
    
    def test_ast_pp(self):
        tree = ast_pe.utils.get_ast(sample_fn)
        s = ast_pe.astpretty.ast_to_string(tree)
        print s


def sample_fn(x, y, foo='bar', **kw):
    if foo == 'bar':
        return x + y
    else:
        return kw['zzz']

if __name__ == '__main__':
    unittest.main()

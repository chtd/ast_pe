# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import BaseTestCase, shift_source
from ast_pe.inliner import Inliner


class TestInliner(BaseTestCase):
    def test_mutiple_returns(self):
        source = '''
        def f(x, y, z='foo'):
            if x:
                b = y + x
                return b
            else:
                return z
        '''
        ast_tree = ast.parse(shift_source(source))
        expected_source = '''
        def f(__ast_pe_var_4, __ast_pe_var_5, __ast_pe_var_6='foo'):
            if __ast_pe_var_4:    
                __ast_pe_var_7 = (__ast_pe_var_5 + __ast_pe_var_4)
                __ast_pe_var_8 = __ast_pe_var_7
                break
            else:    
                __ast_pe_var_8 = __ast_pe_var_6
                break
        '''
        mangler = Inliner(3)
        new_ast = mangler.visit(ast_tree)
        self.assertASTEqual(new_ast, ast.parse(shift_source(expected_source)))
        self.assertEqual(mangler.get_var_count(), 8)
        self.assertEqual(mangler.get_return_var(), '__ast_pe_var_8')
        self.assertEqual(mangler.get_bindings(), {
            'x': '__ast_pe_var_4',
            'y': '__ast_pe_var_5',
            'z': '__ast_pe_var_6',
            'b': '__ast_pe_var_7'})

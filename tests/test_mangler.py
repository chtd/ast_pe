# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import BaseTestCase, shift_source
from ast_pe.mangler import Mangler


class TestMangler(BaseTestCase):
    def test(self):
        self._test('''
        def f(x, y, z='foo'):
            if x:
                b = y + x
                return b
            else:
                return z
        ''',
        '''
        def f(__ast_pe_var_1, __ast_pe_var_2, __ast_pe_var_3='foo'):
            if __ast_pe_var_4:    
                __ast_pe_var_5 = (__ast_pe_var_6 + __ast_pe_var_7)
                return __ast_pe_var_8
            else:    
                return __ast_pe_var_9
        '''
        )

    def _test(self, source, expected_source):
        ast_tree = ast.parse(shift_source(source))
        mangler = Mangler(0)
        new_ast = mangler.visit(ast_tree)
        self.assertASTEqual(new_ast, ast.parse(shift_source(expected_source)))
        return mangler

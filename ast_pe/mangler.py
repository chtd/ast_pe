# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import new_var_name


class Mangler(ast.NodeTransformer):
    ''' Mangle all variable names
    '''
    def __init__(self, var_count_start):
        self._var_count = 0
        self._mangled = {} # {original name -> mangled name}

    def visit_Name(self, node):
        ''' Replacing known variables with literal values
        '''
        self.generic_visit(node)
        if node.id in self._mangled:
            mangled_id = self._mangled[node.id]
        else:
            self._var_count += 1
            mangled_id = new_var_name(self._var_count)
        return ast.Name(id=mangled_id, ctx=node.ctx)


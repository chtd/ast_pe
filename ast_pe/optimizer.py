# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import ast_to_string


class Optimizer(ast.NodeTransformer):
    def __init__(self, bindings):
        ''' 
        bindings is a dict names-> values of variables known at compile time,
        that is populated with newly bound variables (results of calculations
        done at compile time)
        '''
        self.bindings = bindings
        super(Optimizer, self).__init__()
    
    # TODO - handle variable mutation and assignment, 
    # to kick things from bindings
    
    number_types = (int, long, float)
    string_types = (str, unicode)

    def visit_Name(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load) and node.id in self.bindings:
            value = self.bindings[node.id]
            value_type = type(value)
            if value_type in self.number_types:
                return ast.Num(value, 
                        lineno=node.lineno, col_offset=node.col_offset)
            elif value_type in self.string_types:
                return ast.Str(value,
                        lineno=node.lineno, col_offset=node.col_offset)
        return node

    def visit_If(self, node):
        # TODO - visit if part first, than decide which parts to visit
        self.generic_visit(node)
        def choose_branch(test_value):
            if test_value:
                return node.body or ast.Pass()
            else:
                return node.orelse or ast.Pass()
        if isinstance(node.test, ast.Name):
            name = node.test
            if isinstance(name.ctx, ast.Load) and name.id in self.bindings:
                return choose_branch(self.bindings[name.id])
        elif isinstance(node.test, ast.Num):
            return choose_branch(node.test.n)
        elif isinstance(node.test, ast.Str):
            return choose_branch(node.test.s)
        return node


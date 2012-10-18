# -*- encoding: utf-8 -*-

import ast


class VarVisitor(ast.NodeVisitor):
    ''' Collects variables that are candidates for removement
    '''
    # TODO - here we should check for mutations like in Optimizer.visit_Call

    def __init__(self):
        super(VarVisitor, self).__init__()

        self.stored_vars = set()
        self.stored_once_vars = {}
        self.stored_simple_vars = {} # "a = b" or "a = literal"

        self.used_once_vars = set()
        self.used_vars = set()

    def visit_Name(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load):
            if node.id in self.used_vars:
                self.used_once_vars.remove(node.id)
            else:
                self.used_once_vars.add(node.id)
                self.used_vars.add(node.id)


        elif isinstance(node.ctx, ast.Store):
            if node.id in self.stored_vars:
                del self.stored_once_vars[node.id]
            else:
                self.stored_vars.add(node.id)
                #self.stored_once_vars[node.id] = 





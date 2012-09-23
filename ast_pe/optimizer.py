# -*- encoding: utf-8 -*-

import ast
import numbers

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

    def visit_Name(self, node):
        self.generic_visit(node)
        print 'visit_Name', self.bindings
        print ast_to_string(node)
        if isinstance(node.ctx, ast.Load) and node.id in self.bindings:
            value = self.bindings[node.id]
            if isinstance(value, numbers.Number):
                print 'substitute with number', value
                return ast.Num(value, 
                        lineno=node.lineno, col_offset=node.col_offset)
            elif isinstance(value, basestring):
                print 'substitute with string', value
                return ast.Str(value,
                        lineno=node.lineno, col_offset=node.col_offset)
            else:
                pass # TODO
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        print 'visit_If'
        print ast_to_string(node)
        #import pdb; pdb.set_trace()
        #if isinstance(node.test, ast.Compare):
            # pass if isinstance
        return node


# -*- encoding: utf-8 -*-

import ast

from ast_pe.utils import ast_to_string

# FIXME - it SHOULD interleave with Optimizer, so not clear what will stay here

# FIXME - it operates on AST for now, but should operate on CFG instread,
# will change it later, should be easyish


class DataFlow(object):
    ''' Contains results of the data flow analysis
    '''
    def __init__(self):
        self.reassigned_variables = set()
        self.mutated_variables = set()
        self.mutated_node_values = set()


class DataFlowAnalyzer(ast.NodeVisitor):
    ''' Collect nodes whose values are mutated, or may be mutated
    (if they escape given function), or reassigned.
    This information is used by the Optimizer to decide when it it safe
    to evaluate expressions that seem to be known at optimization time.
    '''
    def __init__(self):
        self.data_flow = DataFlow()
        super(DataFlowAnalyzer, self).__init__()

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Attribute):
            # FIXME???
            self.data_flow.mutated_variables.add(node.func.value.id)
        print ast_to_string(node)

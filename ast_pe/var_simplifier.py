# -*- encoding: utf-8 -*-

import ast
from meta.asttools import get_symbols


class VarVisitor(ast.NodeVisitor):
    ''' Collects variables that are candidates for removement
    '''
    # TODO - here we should check for mutations like in Optimizer.visit_Call

    def __init__(self):
        super(VarVisitor, self).__init__()
        self.stored_vars = set()
        self.stored_once_vars = {}

    def visit_Name(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Store):
            if node.id in self.stored_vars:
                del self.stored_once_vars[node.id]
            else:
                self.stored_vars.add(node.id)
                #self.stored_once_vars[node.id] = 



def remove_assignments(node_list):
    ''' Remove one assigment at a time, touching only top level block (???)
    '''
    for node in node_list:
        if isinstance(node, ast.Assign):
            if _can_remove(node, node_list):
                pass


def _can_remove(assign_node, node_list):
    ''' Remove it iff:
     * it is "simple"
     * result it not used in "Load" context elsewhere
    '''
    if len(assign_node.targets) == 1 and \
            isinstance(assign_node.targets[0], ast.Name):
        assigned_name = assign_node.targets[0].id
        idx = node_list.index(assign_node)
        # dummy node for get_symbols, to check no more assignments are made
        dummy_node = ast.While(
                test=ast.Name(id='True', ctx=ast.Load()),
                body=node_list[:idx] + node_list[idx+1:],
                orelse=[])
        if all(n.id != assigned_name 
                for n in get_symbols(dummy_node, (ast.Store, ))):
            return True
    return False


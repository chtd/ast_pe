# -*- encoding: utf-8 -*-

import ast
from meta.asttools import get_symbols

from ast_pe.utils import ast_to_string



def remove_assignments(node_list):
    ''' Remove one assigment at a time, touching only top level block (???)
    '''
    idx = 0
    while idx <= len(node_list) - 1:
        node = node_list[idx]
        removed = _maybe_remove(node, node_list)
        if not removed:
            idx += 1


def _maybe_remove(node, node_list):
    if isinstance(node, ast.Assign):
        can_remove, var_name, value_node = \
                _can_remove_assignment(node, node_list)
        if can_remove:
            node_list.remove(node)
            new_nodes = []
            for n in list(node_list):
                new_n = Replacer(var_name, value_node).visit(n)
                if new_n is not None:
                    new_nodes.append(new_n)
            node_list[:] = new_nodes
            return True


def _can_remove_assignment(assign_node, node_list):
    ''' Can remove it iff:
     * it is "simple"
     * result it not used in "Store" context elsewhere
    '''
    if len(assign_node.targets) == 1 and \
            isinstance(assign_node.targets[0], ast.Name):
        value_node = assign_node.value
        if isinstance(value_node, ast.Name) or \
                isinstance(value_node, ast.Num) or \
                isinstance(value_node, ast.Str):
            # value_node is "simple"
            assigned_name = assign_node.targets[0].id
            idx = node_list.index(assign_node)
            # dummy node for get_symbols, to check no more assignments are made
            dummy_node = ast.While(
                    test=ast.Name(id='True', ctx=ast.Load()),
                    body=node_list[:idx] + node_list[idx+1:],
                    orelse=[])
            if all(n != assigned_name 
                    for n in get_symbols(dummy_node, (ast.Store, ))):
                return True, assigned_name, value_node
    return False, None, None


class Replacer(ast.NodeTransformer):
    ''' Replaces uses of var_name with value_node
    '''
    def __init__(self, var_name, value_node):
        self.var_name = var_name
        self.value_node = value_node
        super(Replacer, self).__init__()

    def visit_Name(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load) and node.id == self.var_name:
            return self.value_node
        else:
            return node
        

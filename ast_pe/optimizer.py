# -*- encoding: utf-8 -*-

import __builtin__

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
    
    NUMBER_TYPES = (int, long, float)
    STRING_TYPES = (str, unicode)
    PURE_FUNCTIONS = (
            abs, divmod,  staticmethod,
            all, enumerate, int, ord, str,
            any,  isinstance, pow, sum,
            basestring, issubclass, super,
            bin,  iter, property, tuple,
            bool, filter, len, range, type,
            bytearray, float, list, unichr,
            callable, format,  reduce, unicode,
            chr, frozenset, long,
            classmethod, getattr, map, repr, xrange,
            cmp,  max, reversed, zip,
            hasattr,  round,
            complex, hash, min, set, apply,
            help, next,
            dict, hex, object, slice, coerce,
            dir, id, oct, sorted,
            )

    # TODO - handle variable mutation and assignment, 
    # to kick things from bindings
    
    def visit_Name(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load) and node.id in self.bindings:
            value = self.bindings[node.id]
            value_type = type(value)
            if value_type in self.NUMBER_TYPES:
                return ast.Num(value, 
                        lineno=node.lineno, col_offset=node.col_offset)
            elif value_type in self.STRING_TYPES:
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

    def visit_Call(self, node):
        self.generic_visit(node)
        print ast_to_string(node)
        is_known, fn = self.get_node_value_if_known(node.func)
        if is_known:
            return self.call_fn_if_safe(fn, node)
        return node

    def call_fn_if_safe(self, fn, node):
        ''' Check that we know all fn args, and that fn is pure.
        Than call it and return a node representing the value.
        It we can not call fn, just return node.
        '''
        if self.fn_is_pure(fn):
            args = []
            #for arg_node in 
            pass
        # TODO
        return node 

    def fn_is_pure(self, fn):
        ''' fn has no side effects, and its value is determined only by
        its inputs
        '''
        if fn in self.PURE_FUNCTIONS:
            return True
        else:
            # TODO - check for decorator, or analyze fn body
            return False

    def get_node_value_if_known(self, node):
        ''' Return tuple of boolean(value is know), and value itself
        '''
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if name in self.bindings:
                return True, self.bindings[name]
            else:
                # TODO - how to check builtin redefinitions?
                if hasattr(__builtin__, name):
                    return True, getattr(__builtin__, name)
        return False, None


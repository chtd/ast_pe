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
        self._var_count = 0
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
        is_known, test_value = self._get_node_value_if_known(node.test)
        if is_known:
            if test_value:
                return node.body or ast.Pass()
            else:
                return node.orelse or ast.Pass()
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        is_known, fn = self._get_node_value_if_known(node.func)
        if is_known:
            return self._fn_result_node_if_safe(fn, node)
        return node

    def _fn_result_node_if_safe(self, fn, node):
        ''' Check that we know all fn args, and that fn is pure.
        Than call it and return a node representing the value.
        It we can not call fn, just return node.
        '''
        assert isinstance(node, ast.Call)
        if self._is_pure_fn(fn):
            args = []
            for arg_node in node.args:
                is_known, value = self._get_node_value_if_known(arg_node)
                if is_known:
                    args.append(value)
                else:
                    return node
            # TODO - cases listed below
            assert not node.kwargs and not node.keywords and not node.starargs
            # TODO - handle exceptions 
            fn_value = fn(*args)
            var_name = self._add_new_binding(fn_value)
            var_node = ast.Name(id=var_name, ctx=ast.Load(),
                    lineno=node.lineno, col_offset=node.col_offset) 
            # self.generic_visit(var_node) - TODO - apply other optimizations
            return var_node
        return node 

    def _is_pure_fn(self, fn):
        ''' fn has no side effects, and its value is determined only by
        its inputs
        '''
        if fn in self.PURE_FUNCTIONS:
            return True
        else:
            # TODO - check for decorator, or analyze fn body
            return False

    def _get_node_value_if_known(self, node):
        ''' Return tuple of boolean(value is know), and value itself
        '''
        known = lambda x: (True, x)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if name in self.bindings:
                return known(self.bindings[name])
            else:
                # TODO - how to check builtin redefinitions?
                if hasattr(__builtin__, name):
                    return known(getattr(__builtin__, name))
        elif isinstance(node, ast.Num):
            return known(node.n)
        elif isinstance(node, ast.Str):
            return known(node.s)
        return False, None
    
    def _add_new_binding(self, value):
        ''' Generate unique variable name, add it to bindings with given value,
        and return the name.
        '''
        self._var_count += 1
        var_name = '__ast_pe_var_%d' % self._var_count
        self.bindings[var_name] = value
        return var_name

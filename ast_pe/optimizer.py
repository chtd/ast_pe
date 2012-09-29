# -*- encoding: utf-8 -*-

import __builtin__
import logging

import ast
from ast_pe.utils import ast_to_string


logger = logging.getLogger(name=__name__)
logger.setLevel(logging.INFO)


class Optimizer(ast.NodeTransformer):
    
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

    def __init__(self, bindings):
        ''' 
        bindings is a dict names-> values of variables known at compile time,
        that is populated with newly bound variables (results of calculations
        done at compile time)
        '''
        self.bindings = bindings
        self._var_count = 0
        self._depth = 0
        super(Optimizer, self).__init__()
   
    def generic_visit(self, node):
        prefix = '--' * self._depth
        logger.debug('%s visit %s', prefix, ast_to_string(node))
        self._depth += 1
        node = super(Optimizer, self).generic_visit(node)
        self._depth -= 1
        logger.debug('%s got %s', prefix, ast_to_string(node))
        return node
    
    def visit_Name(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load) and node.id in self.bindings:
            literal_node = self._get_literal_node(
                    self.bindings[node.id], node)
            if literal_node is not None:
                return literal_node
        return node

    def visit_If(self, node):
        node.test = self.visit(node.test)
        is_known, test_value = self._get_node_value_if_known(node.test)
        if is_known:
            pass_ = ast.Pass(lineno=node.lineno, col_offset=node.col_offset)
            if test_value:
                if node.body:
                    return self._visit(node.body) or pass_
                else:
                    return pass_
            else:
                if node.orelse:
                    return self._visit(node.orelse) or pass_
                else:
                    return pass_
        self.generic_visit(node)
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        is_known, fn = self._get_node_value_if_known(node.func)
        if is_known:
            return self._fn_result_node_if_safe(fn, node)
        return node
    
    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            is_known, value = self._get_node_value_if_known(node.operand)
            if is_known:
                return self._new_binding_node(not value, node)
        return node

    def visit_BoolOp(self, node):
        ''' and, or - handle short-circuting
        '''
        assert type(node.op) in (ast.And, ast.Or)
        new_value_nodes = []
        for value_node in node.values:
            value_node = self.visit(value_node)
            is_known, value = self._get_node_value_if_known(value_node)
            if is_known:
                if isinstance(node.op, ast.And):
                    if not value:
                        return self._new_binding_node(False, node)
                elif isinstance(node.op, ast.Or):
                    if value:
                        return self._new_binding_node(value, node)
            else:
                new_value_nodes.append(value_node)
        if not new_value_nodes:
            return self._new_binding_node(True, node)
        elif len(new_value_nodes) == 1:
            return new_value_nodes[0]
        else:
            node.values = new_value_nodes
            return node
    
    def visit_Compare(self, node):
        ''' ==, >, etc. - evaluate only if all are know (FIXME)
        '''
        self.generic_visit(node)
        is_known, value = self._get_node_value_if_known(node.left)
        if not is_known:
            return node
        value_list = [value]
        for value_node in node.comparators:
            is_known, value = self._get_node_value_if_known(value_node)
            if not is_known:
                return node
            value_list.append(value)
        for a, b, op in zip(value_list, value_list[1:], node.ops):
            result = {
                    ast.Eq: lambda : a == b,
                    ast.Lt: lambda : a < b,
                    ast.Gt: lambda : a > b,
                    ast.GtE: lambda : a >= b, 
                    ast.LtE: lambda : a <= b, 
                    ast.NotEq: lambda : a != b,
                    }[type(op)]()
            if not result:
                return self._new_binding_node(False, node)
        return self._new_binding_node(True, node)

    def _visit(self, node):
        if isinstance(node, list):
            return map(self.visit, node)
        else:
            return self.visit(node)

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
            try:
                fn_value = fn(*args)
            except:
                # do not optimize the call away to leave original exception
                return node
            else:
                return self._new_binding_node(fn_value, node)
        return node 

    def _is_pure_fn(self, fn):
        ''' fn has no side effects, and its value is determined only by
        its inputs
        '''
        if fn in self.PURE_FUNCTIONS:
            return True
        else:
            # TODO - implement decorator
            if getattr(fn, '_ast_pe_is_pure', False):
                return True
            # TODO - or analyze fn body
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

    def _get_literal_node(self, value, replaced_node):
        kwargs = dict(lineno=replaced_node.lineno, 
                col_offset=replaced_node.col_offset)
        if type(value) in self.NUMBER_TYPES:
            return ast.Num(value, **kwargs)
        elif type(value) in self.STRING_TYPES:
            return ast.Str(value, **kwargs)
        elif value is False or value is True:
            return ast.Name(
                    id='True' if value else 'False', ctx=ast.Load(), **kwargs)
    
    def _new_binding_node(self, value, replaced_node):
        ''' Generate unique variable name, add it to bindings with given value,
        and return the node that loads generated variable.
        '''
        literal_node = self._get_literal_node(value, replaced_node)
        if literal_node is not None:
            return literal_node
        else:
            self._var_count += 1
            var_name = '__ast_pe_var_%d' % self._var_count
            self.bindings[var_name] = value
            return ast.Name(id=var_name, ctx=ast.Load(),
                    lineno=replaced_node.lineno, 
                    col_offset=replaced_node.col_offset) 

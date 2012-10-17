# -*- encoding: utf-8 -*-

import __builtin__
import ast
import operator

from ast_pe.utils import ast_to_string, get_logger, fn_to_ast


logger = get_logger(__name__, debug=False)


def optimized_ast(ast_tree, constants):
    ''' Try running Optimizer until it finishes without rollback.
    Return optimized AST and a list of bindings that the AST needs.
    '''
    optimizer = Optimizer(constants)
    while True:
        try:
            new_ast = optimizer.visit(ast_tree)
        except Optimizer.Rollback:
            logger.debug('rollback', exc_info=True)
            # we gathered more knowledge and want to try again
            continue
        else:
            all_bindings = constants
            all_bindings.update(optimizer.get_bindings())
            return new_ast, all_bindings


# FIXME - it operates on AST for now, but should operate on CFG instread,
# will change it later, should be easyish???


class Optimizer(ast.NodeTransformer):
    ''' Simplify AST, given information about what variables are known
    '''
    class Rollback(Exception): pass

    NUMBER_TYPES = (int, long, float)
    STRING_TYPES = (str, unicode)

    # build-in functions that return the same result for the same arguments
    # and do not change their arguments or global environment
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

    def __init__(self, constants):
        ''' 
        :constants: a dict names-> values of variables known at compile time
        '''
        self._constants = dict(constants)
        self._var_count = 0
        self._depth = 0
        self._mutated_nodes = set()
        self._current_block = None # None, or a list of nodes that correspond
        # to currently visited code block
        super(Optimizer, self).__init__()
    
    def get_bindings(self):
        ''' Return a dict, populated with newly bound variables 
        (results of calculations done at compile time), and survived
        initial constants.
        '''
        return self._constants

    def generic_visit(self, node):
        ''' Completly substite parent class "generic_visit", in order to
        be able to insert some code at the line before current expression
        (e.g. when inlining functions).
        Also do some logging.
        '''
        prefix = '--' * self._depth
        logger.debug('%s visit:\n%s', prefix, ast_to_string(node))
        self._depth += 1
        # copy-paste from ast.py, added self._current_block handling 
        block_fields = ['body', 'orelse'] # TODO more?
        for field, old_value in ast.iter_fields(node):
            old_value = getattr(node, field, None)
            if isinstance(old_value, list):
                new_values = []
                if field in block_fields:
                    parent_block = self._current_block 
                    self._current_block = new_values 
                try:
                    for value in old_value:
                        if isinstance(value, ast.AST):
                            value = self.visit(value)
                            if value is None:
                                continue
                            elif not isinstance(value, ast.AST):
                                new_values.extend(value)
                                continue
                        new_values.append(value)
                    old_value[:] = new_values
                finally: # restore self._current_block
                    if field in block_fields:
                        self._current_block = parent_block
            elif isinstance(old_value, ast.AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        # end of copy-paste
        self._depth -= 1
        logger.debug('%s result:\n%s', prefix, ast_to_string(node))
        return node
    
    def visit_FunctionDef(self, node):
        ''' Dead code elimination
        '''
        self.generic_visit(node)
        node.body = self._eliminate_dead_code(node.body)
        return node

    def visit_Name(self, node):
        ''' Replacing known variables with literal values
        '''
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load) and node.id in self._constants:
            literal_node = self._get_literal_node(self._constants[node.id])
            if literal_node is not None:
                return literal_node
        return node

    def visit_If(self, node):
        ''' Leave only one branch, if possible
        '''
        node.test = self.visit(node.test)
        is_known, test_value = self._get_node_value_if_known(node.test)
        if is_known:
            pass_ = ast.Pass()
            taken_node = node.body if test_value else node.orelse
            if taken_node:
                return self._visit(taken_node) or pass_
            else:
                return pass_
        else:
            node.body = self._visit(node.body)
            node.orelse = self._visit(node.orelse)
        return node

    def visit_Call(self, node):
        ''' Make a call, if it is a pure function,
        and handle mutations otherwise.
        Inline function if it is marked with @inline.
        '''
        self.generic_visit(node)
        is_known, fn = self._get_node_value_if_known(node.func)
        if is_known:
            if self._is_inlined_fn(fn):
                inlined_nodes, result_node = self._inlined_fn(node)
                self._current_block.extend(inlined_nodes)
                return result_node
            elif self._is_pure_fn(fn):
                return self._fn_result_node_if_safe(fn, node)
        else:
            # check for mutations from function call:
            # if we don't know it's pure, it can mutate the arguments
            for arg_node in node.args:
                if is_load_name(arg_node):
                    self._mark_mutated_node(arg_node)
                else:
                    # TODO - ???
                    pass
            # if this a method call, it can also mutate "self"
            if isinstance(node.func, ast.Attribute):
                # TODO - with proper dataflow analysis and getattr hanling
                # this code should not be reached
                obj_node, attr = node.func.value, node.func.attr
                if is_load_name(obj_node):
                    self._mark_mutated_node(obj_node)
                else:
                    # TODO - well, it is hard, cause it can be something like
                    # Fooo(x).transform() that also mutates x.
                    # Above this case will be handled by argument mutation
                    # and dataflow analysis, but maybe there are other cases?
                    pass
        return node
    
    def visit_UnaryOp(self, node):
        ''' Hanle "not" - evaluate if possible
        '''
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            is_known, value = self._get_node_value_if_known(node.operand)
            if is_known:
                return self._new_binding_node(not value)
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
                        return self._new_binding_node(False)
                elif isinstance(node.op, ast.Or):
                    if value:
                        return self._new_binding_node(value)
            else:
                new_value_nodes.append(value_node)
        if not new_value_nodes:
            return self._new_binding_node(isinstance(node.op, ast.And))
        elif len(new_value_nodes) == 1:
            return new_value_nodes[0]
        else:
            node.values = new_value_nodes
            return node
    
    def visit_Compare(self, node):
        ''' ==, >, etc. - evaluate only if all are know
        '''
        # TODO - can evaluate if only some are known
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
                return self._new_binding_node(False)
        return self._new_binding_node(True)
    
    def visit_BinOp(self, node):
        ''' Binary arithmetic - + * / etc.
        Evaluate if everything is known.
        '''
        self.generic_visit(node)
        operations = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.div, # TODO - detect truediv!
                ast.Mod: operator.mod,
                ast.Pow: operator.pow,
                ast.LShift: operator.lshift,
                ast.RShift: operator.rshift,
                ast.BitOr: operator.or_,
                ast.BitAnd: operator.and_,
                ast.BitXor: operator.xor,
                ast.FloorDiv: operator.floordiv,
                }
        # FIXME - call l_value.__add__(r_value), etc.
        # than we can get rid of NUMBER_TYPES check
        can_apply = lambda is_known, value: is_known and \
                type(value) in self.NUMBER_TYPES
        if type(node.op) in operations:
            is_known, l_value = self._get_node_value_if_known(node.left)
            if can_apply(is_known, l_value):
                is_known, r_value = self._get_node_value_if_known(node.right)
                if can_apply(is_known, r_value):
                    value = operations[type(node.op)](l_value, r_value)
                    return self._new_binding_node(value)
        return node

    def _visit(self, node):
        ''' Similar to generic_visit - node can be a list, or an AST node.
        For list we visit all elements and collect results, also eliminating
        dead code.
        '''
        if isinstance(node, list):
            result = []
            parent_block = self._current_block
            self._current_block = result
            try:
                for n in node:
                    r = self.visit(n)
                    if isinstance(r, list):
                        result.extend(r)
                    else:
                        result.append(r)
                return self._eliminate_dead_code(result)
            finally:
                self._current_block = parent_block
        else:
            return self.visit(node)

    def _eliminate_dead_code(self, node_list):
        ''' Dead code elimination - remove "pass", code after return
        '''
        for i, node in enumerate(list(node_list)):
            if isinstance(node, ast.Pass) and len(node_list) > 1:
                node_list.remove(node)
            if isinstance(node, ast.Return):
                return node_list[:i+1]
        return node_list

    def _fn_result_node_if_safe(self, fn, node):
        ''' Check that we know all fn args.
        Than call it and return a node representing the value.
        It we can not call fn, just return node.
        Assume that fn is pure.
        '''
        assert isinstance(node, ast.Call) and self._is_pure_fn(fn)
        args = []
        for arg_node in node.args:
            is_known, value = self._get_node_value_if_known(arg_node)
            if is_known:
                args.append(value)
            else:
                return node
        # TODO - cases listed in assert
        assert not node.kwargs and not node.keywords and not node.starargs
        try:
            fn_value = fn(*args)
        except:
            # do not optimize the call away to leave original exception
            return node
        else:
            return self._new_binding_node(fn_value)
    
    def _inlined_fn(self, node):
        ''' Return a list of nodes, representing inlined function call,
        and a node, repesenting the variable that stores result.
        '''
        is_known, fn = self._get_node_value_if_known(node.func)
        assert is_known
        fn_ast = fn_to_ast(fn)
        print ast_to_string(fn_ast)
        print ast_to_string(node)
        #import pdb; pdb.set_trace()
        # TODO:
        # mangle locals (including arguments) in fn_ast
        # if there is no single return at the end, simulate it with while loop
        # FIXME - here just a simple test
        return [ast.Expr(node)], node

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
    
    def _is_inlined_fn(self, fn):
        ''' fn should be inlined
        '''
        return bool(getattr(fn, '_ast_pe_inline', False))

    def _get_node_value_if_known(self, node):
        ''' Return tuple of boolean(value is know), and value itself
        '''
        known = lambda x: (True, x)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if name in self._constants:
                return known(self._constants[name])
            else:
                # TODO - how to check builtin redefinitions?
                if hasattr(__builtin__, name):
                    return known(getattr(__builtin__, name))
        elif isinstance(node, ast.Num):
            return known(node.n)
        elif isinstance(node, ast.Str):
            return known(node.s)
        return False, None

    def _get_literal_node(self, value):
        ''' If value can be represented as literal value, 
        return AST node for it. Literals are never mutable!
        '''
        if type(value) in self.NUMBER_TYPES:
            return ast.Num(value)
        elif type(value) in self.STRING_TYPES:
            return ast.Str(value)
        elif value is False or value is True:
            return ast.Name(id='True' if value else 'False', ctx=ast.Load())
    
    def _new_binding_node(self, value):
        ''' Generate unique variable name, add it to constants with given value,
        and return the node that loads generated variable.
        '''
        literal_node = self._get_literal_node(value)
        if literal_node is not None:
            return literal_node
        else:
            self._var_count += 1
            var_name = '__ast_pe_var_%d' % self._var_count
            self._constants[var_name] = value
            return ast.Name(id=var_name, ctx=ast.Load())

    def _mark_mutated_node(self, node):
        ''' Mark that node holding some variable can be mutated, 
        and propagate this information up the dataflow graph
        '''
        assert is_load_name(node)
        self._mutated_nodes.add(node)
        # TODO - propagate up the dataflow graph
        if node.id in self._constants:
            # obj can be mutated, and we can not assume we know it
            # so we have to rollback here
            del self._constants[node.id]
            raise self.Rollback('%s is mutated' % node.id)


def is_load_name(node):
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)

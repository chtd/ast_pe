"""Python AST pretty-printer.

This module exports a function that can be used to print a human-readable
version of the AST.
"""
__author__ = 'Martin Blais <blais@furius.ca>'

import sys
import ast
from StringIO import StringIO


__all__ = ('print_ast', 'ast_to_string')


def print_ast(ast, indent='    ', stream=sys.stdout, initlevel=0):
    "Pretty-print an AST to the given output stream."
    rec_node(ast, stream.write, initlevel, indent)
    stream.write('\n')


def ast_to_string(ast, indent='    ', initlevel=0):
    "Return pretty-printed AST as a string."
    s = StringIO()
    rec_node(ast, s.write, initlevel, indent)
    return s.getvalue()


def rec_node(node, write, level=0, indent='    '):
    "Recurse through a node, pretty-printing it."
    pfx = indent * level
    if isinstance(node, ast.AST):
        write(pfx)
        write(node.__class__.__name__)
        write('(')
        
        if any(isinstance(child, ast.AST) for child in node.body):
            for i, child in enumerate(node.body):
                if i != 0:
                    write(',')
                write('\n')
                rec_node(child, write, level+1, indent)
            write('\n')
            write(pfx)
        else:
            # None of the children as nodes, simply join their repr on a single
            # line.
            write(', '.join(repr(child) for child in node.body))

        write(')')

    else:
        write(pfx)
        write(repr(node))

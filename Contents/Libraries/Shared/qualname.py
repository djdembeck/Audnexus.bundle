"""
Module to find out the qualified name of a class.
"""

import ast
import inspect

__all__ = ['qualname']

_cache = {}


class _Visitor(ast.NodeVisitor):
    def __init__(self):
        self.stack = []
        self.qualnames = {}

    def store_qualname(self, lineno):
        qn = ".".join(n for n in self.stack)
        self.qualnames[lineno] = qn

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.store_qualname(node.lineno)
        self.stack.append('<locals>')
        self.generic_visit(node)
        self.stack.pop()
        self.stack.pop()

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        self.store_qualname(node.lineno)
        self.generic_visit(node)
        self.stack.pop()


def qualname(obj):
    """Find out the qualified name for a class or function."""

    # For Python 3.3+, this is straight-forward.
    if hasattr(obj, '__qualname__'):
        return obj.__qualname__

    # For older Python versions, things get complicated.
    # Obtain the filename and the line number where the
    # class/method/function is defined.
    try:
        filename = inspect.getsourcefile(obj)
    except TypeError:
        return obj.__qualname__  # raises a sensible error
    if inspect.isclass(obj):
        try:
            _, lineno = inspect.getsourcelines(obj)
        except (OSError, IOError):
            return obj.__qualname__  # raises a sensible error
    elif inspect.isfunction(obj) or inspect.ismethod(obj):
        if hasattr(obj, 'im_func'):
            # Extract function from unbound method (Python 2)
            obj = obj.im_func
        try:
            code = obj.__code__
        except AttributeError:
            code = obj.func_code
        lineno = code.co_firstlineno
    else:
        return obj.__qualname__  # raises a sensible error

    # Re-parse the source file to figure out what the
    # __qualname__ should be by analysing the abstract
    # syntax tree. Use a cache to avoid doing this more
    # than once for the same file.
    qualnames = _cache.get(filename)
    if qualnames is None:
        with open(filename, 'r') as fp:
            source = fp.read()
        node = ast.parse(source, filename)
        visitor = _Visitor()
        visitor.visit(node)
        _cache[filename] = qualnames = visitor.qualnames
    try:
        return qualnames[lineno]
    except KeyError:
        return obj.__qualname__  # raises a sensible error

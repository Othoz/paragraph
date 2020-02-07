"""A module loader wrapping all callables as ops on import

This module defines a module finder/loader pair defining a virtual package ``paragraph.wrap``. Any installed module can be imported within this virtual
package, resulting in all the callables defined in it to be wrapped by the ``paragraph.op`` decorator.

Example:
    >>> from paragraph.wrap.operator import add
    >>> import paragraph as pg
    >>> x = pg.Variable("x")
    >>> y = add.op(x, 2)
"""
from importlib import import_module
from importlib.machinery import ModuleSpec
from typing import Callable

from paragraph.types import op


class WrappedModuleFinder:
    """
    Data package module loader finder. This class sits on `sys.meta_path` and returns the
    loader it knows for a given path, if it knows a compatible loader.
    """

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        """
        This functions is what gets executed by the loader.
        """
        if fullname.startswith("paragraph.wrap"):
            return ModuleSpec(fullname, WrappedModuleLoader())

        return None


class WrappedModuleLoader:
    @classmethod
    def create_module(cls, spec):
        return None

    @classmethod
    def exec_module(cls, module):
        if module.__name__ == "paragraph.wrap":
            module.__path__ = []
            return module

        inner_module_path = module.__name__.split(".", maxsplit=2)[2]
        inner_module = import_module(inner_module_path)

        for func_name in dir(inner_module):
            func = getattr(inner_module, func_name)
            if isinstance(func, Callable):
                module.__dict__[func_name] = op(func)

        module.__path__ = []

        return module

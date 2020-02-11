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
    """Paragraph virtual package finder

    A module finder class that detects the ``paragraph.wrap`` prefix of the virtual package. It delegates the import of any module under that prefix to the
    WrappedModuleLoader class below.

    This class must be appended to ``sys.meta_path`` to be considered by Python's import system.
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
    """Paragraph virtual package loader

    A module loader class that imports modules under the ``paragraph.wrap`` prefix. This loader proceeds as follows:
    - import the underlying module (i.e. the module whose qualified name follows the prefix ``paragraph.wrap``) locally,
    - populate the virtual module with the callables in the underlying module wrapped by ``paragraph.op``.
    """
    @classmethod
    def create_module(cls, spec):
        return None

    @classmethod
    def exec_module(cls, module):
        if module.__name__ == "paragraph.wrap":
            # module.__path__ is required, but may be just an empty list
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

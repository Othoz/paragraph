import sys as _sys

from paragraph._wrapper import WrappedModuleFinder

from paragraph.types import Variable, op  # noqa: F401
from paragraph.session import evaluate, apply, solve, solve_requirements  # noqa: F401

_sys.meta_path.append(WrappedModuleFinder)

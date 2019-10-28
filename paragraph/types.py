"""Class definitions supporting the computation graph"""
import attr

from concurrent.futures import Future
from itertools import chain
from typing import Callable, Dict, Optional, Tuple, List, Any, Iterable, Union
from functools import wraps
from abc import ABC, abstractmethod


@attr.s(eq=False, repr=False, frozen=True)
class Variable:
    """A generic :term:`variable`.

    This class is the return type of all operations in a computation graph. Independent variables can be instantiated directly as follows:

        >>> my_var = Variable(name="my_var")

    Note:
        Type annotations are missing for attributes `op` and `args`, for Sphinx does not seem to cope with forward references.

    Attributes:
        name: a string used to represent the variable. The attribute is mandatory for independent variables and None (the default) otherwise.
        op: the operation producing the variable, of type `Op`.
        args: a dictionary mapping arguments of the above `op` onto their values, of type `Dict[Variable, Any]`.
        dependencies: a dictionary mapping arguments of the above callable onto other variables, of type `Dict[str, Variable]`.
    """
    name = attr.ib(type=Optional[str], default=None)
    op = attr.ib(default=None)
    args = attr.ib(type=Dict, factory=dict)
    dependencies = attr.ib(factory=dict)

    @name.validator
    def _name_only_independent_variable(self, _, value):
        if len(self.dependencies) > 0 and value is not None:
            raise ValueError("Only independent variables can be given a name.")
        if len(self.dependencies) == 0 and value is None:
            raise ValueError("Independent variables must be given a name.")

    def __repr__(self):
        if self.name is not None:
            return self.name

        arg_strings = ["{}={}".format(arg, value) for arg, value in self.args.items()]
        dep_strings = ["{}={}".format(arg, var) for arg, var in self.dependencies.items()]

        return "{}({})".format(self.op, ", ".join(arg_strings + dep_strings))


@attr.s
class Requirement(ABC):
    """Base class for defining a requirement mixin

    A Requirement class defines one or several attributes storing the actual requirement being expressed, and takes complete responsibility of these
    attributes. Therefore, a concrete requirement class should:

        - define default values or factory callbacks for *all* the attributes it introduces,
        - redefine the :meth:`merge` method below appropriately, respecting the prescribed constraints,
        - expose convenience methods to manipulate their attributes, these methods should operate *in place* to avoid unwanted interference with other
          Requirement mixins,
        - provide an implementation of :meth:`__deepcopy__` whenever relevant .

    Deriving a compound requirements class boils down to putting together requirement mixins:

        >>> @attr.s
        >>> class MyRequirements(DateRangeRequirement, DatasetContentsRequirement):
        ...     pass

    assuming `DateRangeRequirement` and `DatasetContentsRequirement` derive from the present class.
    """

    def merge(self, other):
        """Merges `other` into `self` in-place, must be implemented by all cooperating mixin classes.

        The requirement mixins should define the :meth:`merge` method for the attributes they define (and therefore take responsibility for). The computation
        implemented must be both:

            commutative
                the result of `[self.merge(usg) for usg in usages[self]]` does not depend on the order of the usages in the list

            idempotent
                if `usg1 = usg2`, invoking `self.update(usg2)` after `self.update(usg1)` leaves `self` unchanged

        Only under these conditions is it guaranteed that all :term:`backward traversals <backward traversal>` of the computation graph result in the same
        input requirements.

        In addition, every implementation of this method must be *cooperative* and end with the following line:

        .. code::

            super().merge(other)

        Arguments:
            other: the requirement to merge into self, must be of the same concrete type as `self`.
        """
        pass

    def new(self):
        """Return an empty requirement of the same type as self."""
        return type(self)()


@attr.s(repr=False)
class Op(ABC):
    """Abstract base class for computation graph operations.

    A concrete Op class should redefine the :meth:`_run` method, which fully specifies its behavior. Calling an Operation instance results in the following:

        - if no argument is of Variable type, the return value of the :meth:`_run` method is returned,
        - otherwise, a Variable is returned, which represents the result of the operation applied to its arguments.

    Additional requirements can be introduced for variable arguments, globally or individually, by redefining the :meth:`_arg_requirements` method
    appropriately.

    Attributes:
        thread_safe: If False, the op is always executed in the main thread. Defaults to True.
    """
    thread_safe = attr.ib(type=bool, default=True)

    def __repr__(self):
        return type(self).__name__

    @staticmethod
    def split_args(args: Dict) -> Tuple[List[Any], Dict[str, Any]]:
        """Separate positional from keyword arguments in a dict.

        This method extracts `args` entries with a key of type integer, and collates them into a list
        """
        args = args.copy()
        pos_args = [args.pop(k) for k in sorted(filter(lambda x: isinstance(x, int), args))]
        return pos_args, args

    @staticmethod
    def _collect_args(args: Iterable[Any], kwargs: Dict[str, Any]) -> Dict[Union[int, str], Any]:
        """Awaits all arguments and store them in a dictionary, using the index as a key for positional arguments."""
        return {arg: value.result() if isinstance(value, Future) else value for arg, value in chain(enumerate(args), kwargs.items())}

    @abstractmethod
    def _run(self, *args, **kwargs):
        """The function called to evaluate the operation, must be implemented by all concrete classes"""

    def arg_requirements(self, req: Requirement, arg: str = None) -> Requirement:  # pylint: disable=R0201
        """Compute the requirements on the input value for argument `arg` from the requirements `req` bearing on the output variable.

        The base implementation below returns an empty requirement for every argument, preserving the type. Concrete classes should redefine this method
        whenever applicable.

        .. warning::

          This method should never update requirements *in-place*, as this would result in adversary side-effects. The recommended practice is for
          this method to:
          - instantiate a new Requirement instance or deep-copy the passed in `req` if information should be retained,
          - update the new instance using in-place methods exposed by the requirement class, and return it.

          Should the output requirement be returned unmodified, it is however safe to just return its reference as-is.
        """
        return type(req)()

    def __call__(self, *args, **kwargs):
        """Wraps an instance method to work within the computational graph"""
        all_args = self._collect_args(args, kwargs)
        var_args = {arg: var for arg, var in all_args.items() if isinstance(var, Variable)}

        # The following ensures that the wrapper just returns a concrete value in absence of variable arguments
        if len(var_args) == 0:
            pos_args, kw_args = Op.split_args(all_args)
            return self._run(*pos_args, **kw_args)

        static_args = {arg: val for arg, val in all_args.items() if not isinstance(val, Variable)}

        return Variable(op=self, args=static_args, dependencies=var_args)


def op(func: Callable) -> Callable:
    """Wraps a function within an Op object.

    The returned function accepts arguments of type Variable everywhere in its signature, in addition to the types accepted by the decorated function. In
    presence of such arguments, it returns a Variable object symbolizing the result of the operation with the arguments passed in. In absence of variable
    arguments, the function returned is just equivalent to the function passed in, in particular it returns a value of the pristine return type.


    .. warning::
        Operations returned by this decorator are marked thread-safe by default. It is the user's responsibility to set `Op.thread_safe` to `False` where
        appropriate.

    Arguments:
        func: the function to transform into an Op
    """
    class Wrapper(Op):
        def __repr__(self):
            return func.__name__

        def _run(self, *args, **kwargs):
            return func(*args, **kwargs)

    return wraps(func)(Wrapper())

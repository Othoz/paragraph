"""Class definitions supporting the computation graph"""

from typing import Callable, Dict, Any, Optional
from functools import partial, wraps
from itertools import filterfalse

import attr
from attr.validators import optional, instance_of

from abc import ABC, abstractmethod


@attr.s(cmp=False)
class Variable:
    """A generic :term:`variable`.

    This class is the return type of all operations in a computation graph.

    Attributes:
        func: a callable returning the value of the variable given those of the dependencies
        arg_requirements_func: a callable returning the requirements bearing on a dependency given those bearing on the current variable
        dependencies: a dictionary mapping arguments of the above callable onto other variables in the computation graph
    """
    func = attr.ib(type=Optional[Callable], default=attr.Factory(lambda self: lambda: self, takes_self=True), validator=optional(instance_of(Callable)))
    arg_requirements_func = attr.ib(type=Optional[Callable], default=lambda x, y: type(x)(), validator=optional(instance_of(Callable)))
    dependencies = attr.ib(type=Dict[str, Any], factory=dict)


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


@attr.s
class Op(ABC):
    """Abstract base class for computation graph operations.

    A concrete Op class should redefine the :meth:`_run` method, which fully specifies its behavior. Calling an Operation instance results in the following:

        - if no argument is of Variable type, the return value of the :meth:`_run` method is returned,
        - otherwise, a Variable is returned, which represents the result of the operation applied to its arguments.

    Additional requirements can be introduced for variable arguments, globally or individually, by redefining the :meth:`_arg_requirements` method
    appropriately.
    """

    @abstractmethod
    def _run(self, **kwargs):
        """The function called to evaluate the operation, must be implemented by all concrete classes"""

    def _arg_requirements(self, req: Requirement, arg: str = None) -> Requirement:  # pylint: disable=R0201
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
        if len(args) > 0:
            raise RuntimeError("Positional arguments are not supported in computational graphs, use keyword arguments only.")

        var_args = dict(filter(lambda x: isinstance(x[1], Variable), kwargs.items()))

        # The following ensures that the wrapper just returns a concrete value in absence of variable arguments
        if len(var_args) == 0:
            return self._run(**kwargs)

        static_args = dict(filterfalse(lambda x: isinstance(x[1], Variable), kwargs.items()))

        return Variable(func=partial(self, **static_args), arg_requirements_func=self._arg_requirements, dependencies=var_args)


def op(func: Callable) -> Callable:
    """Wraps a function within an Op object.

    The returned function accepts arguments of type Variable everywhere in its signature, in addition to the types accepted by the decorated function. In
    presence of such arguments, it returns a Variable object symbolizing the result of the operation with the arguments passed in. In absence of variable
    arguments, the function returned is just equivalent to the function passed in, in particular it returns a value of the pristine return type.

    Arguments:
        func: the function to transform into an Op
    """

    class Wrapper(Op):
        def _run(self, **kwargs):
            return func(**kwargs)

    return wraps(func)(Wrapper())

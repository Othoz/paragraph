"""
Session
*******

*Algorithms for traversing, solving and evaluating computation graphs*
"""
import warnings

from concurrent.futures import Executor, Future
from itertools import filterfalse
from typing import Dict, Any, List, Generator, Iterable, Optional, Tuple
from collections import defaultdict, deque
from contextlib import contextmanager

from paragraph.types import Variable, Requirement, Op


@contextmanager
def eager_mode():
    """Activate eager mode within a context manager.

    In eager mode, the method ``Op.op`` is replaced with the direct invocation of the underlying method ``Op._run``. In this mode, no variable is emitted,
    allowing to test a computation graph without ever calling ``session.evaluate``.
    """
    op = Op.op
    Op.op = lambda self, *a, **k: self._run(*a, **k)
    yield
    Op.op = op


def traverse_fw(output: Iterable[Variable]) -> Generator[Variable, None, None]:  # noqa: C901
    """Returns a generator implementing a :term:`forward traversal` of the computation subgraph leading to `var`.

    The generator returned guarantees that every dependent variable occurs after all its dependencies upon iterating, whence the name `forward traversal`. When
    generated in this order, variables can be simply evaluated in turn: at each iteration, all dependencies of the current variable will have been evaluated
    already.

    Arguments:
        output: The variables whose dependencies should be traversed.

    Yields:
        All dependencies of the output variables, each variable yielded occurring before the variables depending thereupon.

    Raises:
        ValueError: If a cyclic dependency is detected in the graph.
    """
    visited = []

    for var in output:
        if var in visited:
            continue

        path = [var]

        while len(path) > 0:
            for dep in path[-1].dependencies.values():
                if dep in path:
                    raise ValueError("Cyclic dependency detected for {}, cannot proceed with iteration.".format(dep))
                if dep not in visited:
                    path.append(dep)
                    break
            else:
                yield path[-1]
                visited.append(path.pop())


def _count_usages(output: Iterable[Variable]) -> Dict[Variable, int]:
    """Count the variables directly depending on each dependency.

    Arguments:
        output: The output variables. Their dependencies only are included in the usage counts.

    Returns:
        A dictionary mapping each dependency onto the number of dependent operations.
    """
    usage_counts = defaultdict(lambda: 0)

    for var in traverse_fw(output):
        for dep in var.dependencies.values():
            usage_counts[dep] += 1

    return usage_counts


def _get_arguments(var: Variable, cache: Dict[Variable, Any], usage_counts: Dict[Variable, int], output) -> Tuple[List, Dict]:
    arguments = {}
    for arg, dep in var.dependencies.items():
        usage_counts[dep] -= 1
        if usage_counts[dep] == 0 and dep not in output:
            value = cache.pop(dep)
        else:
            value = cache[dep]
        arguments[arg] = value

    arguments.update(var.args)
    return Op.split_args(arguments)


def evaluate(output: Iterable[Variable], args: Dict[Variable, Any], executor: Optional[Executor] = None) -> List:  # noqa: C901
    """Evaluate the specified output variable.

    The argument values provided through `args` should be:
      - of the type expected by the operations consuming the variable,
      - of type :class:`concurrent.futures.Future`, in which case the result will be awaited by consuming ops. The result should be of the expected type.

    Support of arguments values of type Variable will be dropped in version 2.0 and a DeprecationWarning will be issued. The same applies if any input
    variable required to evaluate the output is left uninitialized.

    Arguments:
      output: The variables to evaluate.
      args: Initialization of the input variables, none of which should have dependencies.
      executor: An instance of concurrent.futures.Executor, to which op evaluations are submitted. If None, the default, evaluation proceeds sequentially.

    Returns:
      A list of values of the same size as `output`. The entry at index `i` is the computed value of `output[i]`.

    Raises:
      ValueError: If a variable in `args` is not an input variable. In this case, the consistency of the results cannot be guaranteed.
    """
    for var in args:
        if not var.isinput():
            raise ValueError("An initialization value is provided for variable {}, but it has dependencies."
                             "Proceeding further could result in an inconsistent evaluation.".format(var))
    cache = args.copy()

    # Discover usages so cached references can be released at earliest opportunity
    usage_counts = _count_usages(output=output)

    for var in traverse_fw(output):
        if var in cache:
            continue

        if var.isinput():
            warnings.warn(f"Variable {var} is uninitialized, some output variables will not be evaluated."
                          f"This functionality will be dropped in version 2.0, use ``session.solve`` instead.",
                          DeprecationWarning)
            cache[var] = var
            continue

        pos_args, kw_args = _get_arguments(var, cache, usage_counts, output)

        if executor is not None and var.op.thread_safe:
            cache[var] = executor.submit(var.op, *pos_args, **kw_args)
        else:
            cache[var] = var.op(*pos_args, **kw_args)

    return [cache[var].result() if isinstance(cache[var], Future) else cache[var] for var in output]


def solve(output: Iterable[Variable], args: Dict[Variable, Any], executor: Optional[Executor] = None) -> List:  # noqa: C901
    """Resolve the specified output variables.

    The argument values provided through `args` should be:
      - of the type expected by the operations consuming the variable,
      - of type Variable, in which case it should evaluate to the above type,
      - of type :class:`concurrent.futures.Future`, in which case the result will be awaited by consuming ops. The result should be of either above types.

    Arguments:
      output: The variables to evaluate.
      args: Initialization of the input variables, none of which should have dependencies.
      executor: An instance of concurrent.futures.Executor, to which op evaluations are submitted. If None, the default, evaluation proceeds sequentially.

    Returns:
      A list of variables of the same size as `output`. The entry at index `i` is the resolved variable for `output[i]`.

    Raises:
      ValueError: If a variable in `args` is not an input variable. In this case, the consistency of the results cannot be guaranteed.
    """
    for var in args:
        if not var.isinput():
            raise ValueError("An initialization value is provided for variable {}, but it has dependencies."
                             "Proceeding further could result in an inconsistent evaluation.".format(var))
    cache = args.copy()

    # Discover usages so cached references can be released at earliest opportunity
    usage_counts = _count_usages(output=output)

    for var in traverse_fw(output):

        if var in cache:
            continue

        if var.isinput():
            cache[var] = var
            continue

        pos_args, kw_args = _get_arguments(var, cache, usage_counts, output)

        if var.isdependent() or var in output:
            cache[var] = var.op.op(*pos_args, **kw_args)
            continue

        # From this point on, the variable is to be evaluated
        if executor is not None and var.op.thread_safe:
            cache[var] = executor.submit(var.op, *pos_args, **kw_args)
        else:
            cache[var] = var.op(*pos_args, **kw_args)

    return [cache[var] for var in output]


def apply(output: List[Variable], args: Dict[Variable, Any], iter_args: Iterable[Dict[Variable, Any]], executor: Optional[Executor] = None)\
        -> Generator[List[Any], None, None]:
    """Iterate the evaluation of a set of output variables over input arguments.

    This function accepts two types of arguments: `args` receives *static* arguments, using which a first evaluation of the output variables is executed;
    then, `iter_args` receives an iterable over input arguments, which are iterated over to resolve the output variables left unresolved after the first
    evaluation. The values of the output variables obtained after each iteration are then yielded. See :meth:`evaluate` for the constraints bearing on the
    types of the values provided in both `args` and `iter_args`.

    Arguments:
      output: The variables to evaluate.
      args: A dictionary mapping input variables onto input values.
      iter_args: An iterable over dictionaries mapping input variables onto input values.
      executor: An instance of concurrent.futures.Executor to which op evaluations are submitted. If None (the default), evaluation proceeds sequentially.

    Yields:
      A list of values of the same size as `output`. The entry at index `i` is the computed value of `output[i]`.

    Raises:
      ValueError: If a dynamic argument assigns a value to a variable appearing in static arguments, as proceeding would produce inconsistent results.
    """
    partial_values = dict(zip(output, solve(output, args=args, executor=executor)))
    unresolved_output_vars = [partial_values[var] for var in output if isinstance(partial_values[var], Variable)]

    for arg_dict in iter_args:
        for var in arg_dict:
            if var in args:
                raise ValueError(f"An initialization value for variable {var} is provided in `iter_args` and in `args`."
                                 f"Proceeding further could result in an inconsistent evaluation.")
        iter_values = dict(zip(unresolved_output_vars, evaluate(unresolved_output_vars, args=arg_dict, executor=executor)))
        yield [partial_values[var] if not isinstance(partial_values[var], Variable) else iter_values[partial_values[var]] for var in output]


#
# Backward algorithms
#

def traverse_bw(output: List[Variable]) -> Generator[Variable, None, None]:
    """Returns a generator implementing a :term:`backward traversal` of `var`'s transitive dependencies.

    This generator guarantees that a variable is yielded after all its usages.

    Note:
      If `var` is in the boundary, the generator exits without yielding any variable.

    Arguments:
        output: The variables whose transitive dependencies should be explored.

    Yields:
        All dependencies of the output variables (stopping at the boundary), each variable is yielded after all variables depending thereupon.
    """
    usage_counts = _count_usages(output)

    # At this stage, skip output variables also present in the dependency path of another output variable
    queue = deque(filterfalse(lambda x: usage_counts[x] > 0, output))

    while len(queue) > 0:

        cur = queue.popleft()

        for dep in cur.dependencies.values():
            usage_counts[dep] -= 1
            if usage_counts[dep] == 0:
                queue.append(dep)

        yield cur


def solve_requirements(output_requirements: Dict[Variable, Requirement]) -> Dict[Variable, Requirement]:
    """Backward propagate requirements from the output variables to their transitive dependencies

    Arguments:
        output_requirements: the requirements to be fulfilled on output

    Returns:
        A dictionary mapping all transitive dependencies of `output` onto their resolved requirement dictionaries
    """
    reqs = output_requirements.copy()

    for var in traverse_bw(list(output_requirements)):
        for arg, dep in var.dependencies.items():
            arg_req = var.op.arg_requirements(reqs[var], arg)
            # Ensure merge operates on a new instance
            if dep not in reqs:
                reqs[dep] = type(arg_req)()
            reqs[dep].merge(arg_req)

    return reqs

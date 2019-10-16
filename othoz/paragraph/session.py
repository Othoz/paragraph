"""Algorithms for traversing and evaluating a computation graph."""

from concurrent.futures import ThreadPoolExecutor, Future
from itertools import filterfalse
from typing import Dict, Any, Optional, List, Generator, Iterable
from collections import defaultdict, deque

from othoz.paragraph.types import Variable, Requirement


def traverse_fw(output: Iterable[Variable], boundary: Optional[List[Variable]] = None) -> Generator[Variable, None, None]:  # noqa: C901
    """Returns a generator implementing a :term:`forward traversal` of the computation subgraph leading to `var`.

    The generator returned guarantees that every dependent variable occurs after all its dependencies upon iterating, whence the name `forward traversal`. When
    generated in this order, variables can be simply evaluated in turn: at each iteration, all dependencies of the current variable will have been evaluated
    already.

    Note:
        If `output` is included in the boundary, the generator returns without yielding any variable.

    Arguments:
        output: The variables whose dependencies should be traversed.
        boundary: An optional list of variables excluded from the generator. Their dependencies are not resolved.

    Yields:
        All dependencies of the output variables (stopping at the boundary), each variable yielded occurring before the variables depending thereupon.

    Raises:
        ValueError: If a cyclic dependency is detected in the graph.
    """
    if boundary is None:
        boundary = []

    visited = []

    for var in output:
        if var in boundary or var in visited:
            continue

        path = [var]

        while len(path) > 0:

            for dep in path[-1].dependencies.values():
                if dep in boundary:
                    continue

                if dep in path:
                    raise ValueError("Cyclic dependency detected for {}, cannot proceed with iteration.".format(dep))

                if dep not in visited:
                    path.append(dep)
                    break

            else:
                yield path[-1]
                visited.append(path.pop())


def _count_usages(output: Iterable[Variable], boundary: List[Variable]) -> Dict[Variable, int]:
    """Count the variables directly depending on each dependency.

    Arguments:
        output: The output variables. Their dependencies only are included in the usage counts.
        boundary: An optional list of variables excluded from the dependencies resolution.

    Returns:
        A dictionary mapping each dependency onto the number of dependent operations.
    """
    usage_counts = defaultdict(lambda: 0)

    for var in traverse_fw(output, boundary=boundary):
        for dep in var.dependencies.values():
            if dep in boundary:
                continue

            usage_counts[dep] += 1

    return usage_counts


def evaluate(output: Iterable[Variable], args: Dict[Variable, Any], max_workers: Optional[int] = 1) -> List:
    """Evaluate the specified output variable.

    The argument values provided through `args` can be of type Variable. In this case, output variables depending on such arguments will evaluate to a new
    instance of Variable.

    Arguments:
      output: The variables to evaluate.
      args: Initialization of the input variables.
      max_workers: The maximum number of threads to run concurrently. If None, this is automatically set to 5 x num_cpus.

    Returns:
      A list of values of the same size as `output`. The entry at index `i` is the computed value of `output[i]`.
    """
    cache = args.copy()

    # Discover usages so cached references can be released at earliest opportunity
    usage_counts = _count_usages(output=output, boundary=list(cache))

    with ThreadPoolExecutor(max_workers=max_workers) as ex:

        for var in traverse_fw(output, boundary=list(cache)):
            arguments = {}

            for arg, dep in var.dependencies.items():
                usage_counts[dep] -= 1
                if usage_counts[dep] == 0 and dep not in output:
                    value = cache.pop(dep)
                else:
                    value = cache[dep]
                arguments[arg] = value

            def func(**args):
                arguments = {arg: value.result() if isinstance(value, Future) else value for arg, value in args.items()}
                return var.func(**arguments)

            cache[var] = ex.submit(func, **arguments)

    return [cache[var].result() if isinstance(cache[var], Future) else cache[var] for var in output]


def apply(output: List[Variable], args: Dict[Variable, Any], iter_args: Iterable[Dict[Variable, Any]], max_workers: int = 1)\
        -> Generator[List[Any], None, None]:
    """Iterate the evaluation of a set of output variables over input arguments.

    This function accepts two types of arguments: `args` receives *static* arguments, using which a first evaluation of the output variables is executed;
    then, `iter_args` receives an iterable over input arguments, which are iterated over to resolve the output variables left unresolved after the first
    evaluation. The values of the output variables obtained after each iteration are then yielded.

    Arguments:
      output: The variables to evaluate.
      args: A dictionary mapping input variables onto input values.
      iter_args: An iterable over dictionaries mapping input variables onto input values.
      max_workers: The maximum number of threads to run concurrently. If None, this is automatically set to 5 x num_cpus.

    Yields:
      A list of values of the same size as `output`. The entry at index `i` is the computed value of `output[i]`.

    Raises:
      ValueError: If a dynamic argument assigns a value to a variable fully resolved by static arguments, as proceeding would produce inconsistent results.
    """
    values = dict(zip(output, evaluate(output, args=args, max_workers=max_workers)))
    variables = [values[var] for var in output if isinstance(values[var], Variable)]

    for args in iter_args:
        for arg in args:
            if not isinstance(values[arg], Variable):
                raise ValueError("iter_args includes a value for variable {}, which is already resolved.".format(arg))

        iter_values = dict(zip(variables, evaluate(variables, args=args, max_workers=max_workers)))

        yield [values[var] if not isinstance(values[var], Variable) else iter_values[values[var]] for var in output]


#
# Backward algorithms
#

def traverse_bw(output: List[Variable], boundary: Optional[List[Variable]] = None) -> Generator[Variable, None, None]:
    """Returns a generator implementing a :term:`backward traversal` of `var`'s transitive dependencies.

    This generator guarantees that a variable is yielded after all its usages.

    Note:
      If `var` is in the boundary, the generator exits without yielding any variable.

    Arguments:
        output: The variables whose transitive dependencies should be explored.
        boundary: An optional list of variables which should be excluded from the generator. Their dependencies are not resolved.

    Yields:
        All dependencies of the output variables (stopping at the boundary), each variable is yielded after all variables depending thereupon.
    """
    if boundary is None:
        boundary = []

    usage_counts = _count_usages(output, boundary)

    # Skip output variables also present in the boundary or the dependency path of another output variable
    queue = deque(filterfalse(lambda x: x in boundary or usage_counts[x] > 0, output))

    while len(queue) > 0:

        cur = queue.popleft()

        for dep in cur.dependencies.values():
            if dep in boundary:
                continue

            usage_counts[dep] -= 1
            if usage_counts[dep] == 0:
                queue.append(dep)

        yield cur


def solve_requirements(output_requirements: Dict[Variable, Requirement], boundary: Optional[List[Variable]] = None) -> Dict[Variable, Requirement]:
    """Backward propagate requirements from the output variable to its transitive dependencies

    Arguments:
        output_requirements: the requirements to be fulfilled on output
        boundary: resolution of requirements stops whenever a Variable in this list is encountered

    Returns:
        A dictionary mapping the dependencies of `output` onto their resolved requirement dictionaries
    """
    reqs = output_requirements.copy()

    for var in traverse_bw(list(output_requirements), boundary=boundary):
        for arg, dep in var.dependencies.items():
            arg_req = var.arg_requirements_func(reqs[var], arg)

            # Ensure merge operates on a new instance
            if dep not in reqs:
                reqs[dep] = type(arg_req)()

            reqs[dep].merge(arg_req)

    return reqs

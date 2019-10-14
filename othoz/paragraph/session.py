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
    """
    usage_counts = defaultdict(lambda: 0)

    for var in traverse_fw(output, boundary=boundary):
        for dep in var.dependencies.values():
            if dep in boundary:
                continue

            usage_counts[dep] += 1

    return usage_counts


def evaluate(output: Iterable[Variable], args: Dict[Variable, Any], max_workers: Optional[int] = 1) -> Any:
    """Evaluate the specified output variable.

    Arguments:
      output: The variables to evaluate.
      args: Initialization of the input variables.
      max_workers: The maximum number of threads to run concurrently. If None, this is automatically set to 5 x num_cpus.
    """
    cache = args.copy()

    # Discover usages so cached references can be released at earliest opportunity
    usage_counts = _count_usages(output=output, boundary=list(cache))

    with ThreadPoolExecutor(max_workers=max_workers) as ex:

        for var in traverse_fw(output, boundary=list(cache)):
            arguments = {}

            for arg, dep in var.dependencies.items():
                if usage_counts[dep] == 1:
                    value = cache.pop(dep)
                else:
                    value = cache[dep]
                arguments[arg] = value
                usage_counts[dep] -= 1

            def func(**args):
                arguments = {arg: value.result() if isinstance(value, Future) else value for arg, value in args.items()}
                return var.func(**arguments)

            cache[var] = ex.submit(func, **arguments)

    print("Collecting results")
    results = {var: cache[var].result() if isinstance(cache[var], Future) else cache[var] for var in output}

    return results


#
# Backward algorithms
#

def traverse_bw(output: List[Variable], boundary: Optional[List[Variable]] = None) -> Generator[Variable, None, None]:
    """Returns a generator implementing a :term:`backward traversal` of `var`'s transitive dependencies.

    This generator guarantees that a variable is yielded after all its usages.

    Note:
      If `var` is in the boundary, the generator exits without yielding any variable.

    Arguments:
        var: The variables whose transitive dependencies should be explored.
        boundary: An optional list of variables which should be excluded from the generator. Their dependencies are not resolved.
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

            if usage_counts[dep] == 1:
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

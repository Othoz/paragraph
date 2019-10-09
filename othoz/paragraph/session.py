from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Optional, List, Generator
from collections import defaultdict, deque

from othoz.paragraph.types import Variable, Requirement


def traverse_fw(var: Variable, boundary: Optional[List[Variable]] = None) -> Generator[Variable, None, None]:  # noqa: C901
    """Returns a generator implementing a :term:`forward traversal` of the computation subgraph leading to `var`.

    The generator returned guarantees that every dependent variable occurs after all its dependencies upon iterating, whence the name `forward traversal`. When
    generated in this order, variables can be simply evaluated in turn: at each iteration, all dependencies of the current variable will have been evaluated
    already.

    Note:
        If `var` is in the boundary, the generator returns without yielding any variable.

    Arguments:

        var: The variable whose dependencies should be traversed. Also the last variable generated before iteration stops, if any.
        boundary: An optional list of variables whose dependencies should not be resolved and should be excluded from the generator.

    Raises:
        ValueError: If a cyclic dependency is detected in the graph.
    """
    if boundary is None:
        boundary = []

    if var in boundary:
        return

    path = [var]
    visited = []

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


def _count_usages(output: Variable, boundary: List[Variable]) -> Dict[Variable, int]:
    usage_counts = defaultdict(lambda: 0)

    for var in traverse_fw(output, boundary=boundary):
        for dep in var.dependencies.values():
            usage_counts[dep] += 1

    return usage_counts


def evaluate(output: Variable, args: Dict[Variable, Any], max_workers: Optional[int] = None) -> Any:
    """Evaluate the specified output variable.

    Arguments:
      output: the variable to evaluate
      args: initialization of the input variables
      pool_type: the type of executor pool to use
      max_workers: the maximum number of executors to run concurrently
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

            def func(**arguments):
                args = {arg: value.result() if isinstance(value, Future) else value for arg, value in arguments.items()}
                return var.func(**args)

            cache[var] = ex.submit(lambda: func(**arguments))

    output_value = cache.get(output)
    if isinstance(output_value, Future):
        output_value = output_value.result()

    return output_value


#
# Backward algorithms
#

def traverse_bw(var: Variable, boundary: Optional[List[Variable]] = None) -> Generator[Variable, None, None]:
    """Returns a generator implementing a :term:`backward traversal` of `var`'s transitive dependencies.

    This generator guarantees that a variable is yielded after all its usages. In this order

    Note:
      If `var` is in the boundary, the generator exits without yielding any variable.

    Arguments:
        var: The variable whose transitive dependencies should be explored. Also the first variable generated.
        boundary: An optional list of variables which should be excluded from the generator, and whose dependencies should not be resolved.
    """
    if boundary is None:
        boundary = []

    if var in boundary:
        return

    usage_counts = _count_usages(var, boundary)
    queue = deque([var])

    yield var

    while len(queue) > 0:

        cur = queue.popleft()
        for dep in cur.dependencies.values():

            usage_counts[dep] -= 1

            if dep in boundary:
                continue

            if usage_counts[dep] == 0:
                yield dep
                queue.append(dep)


def solve_requirements(output: Variable, output_requirements: Requirement, boundary: Optional[List[Variable]] = None) -> Dict[Variable, Requirement]:
    """Backward propagate requirements from the output variable to its transitive dependencies

    Arguments:
        output: the variable on which `output_requirements` apply
        output_requirements: the requirements to be fulfilled on output
        boundary: resolution of requirements stops whenever a Variable in this list is encountered

    Returns:
        A dictionary mapping the dependencies of `output` onto their resolved requirement dictionaries
    """
    reqs = {output: output_requirements}

    for var in traverse_bw(output, boundary=boundary):
        for arg, dep in var.dependencies.items():
            arg_req = var.arg_requirements_func(reqs[var], arg)

            # Ensure merge operates on a new instance
            if dep not in reqs:
                reqs[dep] = type(arg_req)()

            reqs[dep].merge(arg_req)

    return reqs

.. include:: ../../README.rst


Going further
=============

Partial evaluation
''''''''''''''''''

When the arguments passed to `paragraph.session.evaluate` are insufficient to resolve fully an output variable (that is, at least one transitive
dependency of the output variable is left uninitialized), the value returned for the output variable is simply another variable. This new variable has in
general fewer dependencies, for dependencies fully resolved upon evaluation are replaced by their values.

.. note::
  The ambiguity on the type returned by ``paragraph.session.evaluate`` will be lifted in version 2.0. From there on, ``paragraph.session.evaluate`` will raise
  in situations such as described above. The support for partial evaluation will however be continued using the new function ``paragraph.session.solve``.


Mapping over inputs
'''''''''''''''''''

The function `paragraph.session.apply` extends `paragraph.session.evaluate` to take, in addition, an iterator over input arguments to
the computation graph. It takes advantage of partial evaluation to reduce the number of operations evaluated at each iteration.


Concurrency
'''''''''''

Building upon the guarantees granted by a forward traversal, concurrent execution of ops comes at no additional cost. This feature relies on the `concurrent`
package from the Python standard library: ops are simply submitted to an instance of `concurrent.futures.Executor` for evaluation. The executor should
be provided externally and allow calling `concurrent.futures.Future` methods from a submitted callable (in particular, this excludes
`concurrent.futures.ProcessPoolExecutor`). The responsibility for shutting down the executor properly lies on the user. In absence of an executor,
variables are evaluated in a sequential manner, yet still lazily.

Should an operation be executed in the main process, it can be marked as such by setting the attribute `Op.thread_safe` to False.

Example usage:

>>> ...graph definition...
>>> with ThreadPoolExecutor() as ex:
...     res = evaluate([output], args={input: input_value}, executor=ex)

.. note::
    Argument values passed to `paragraph.session.evaluate` can be of type `concurrent.futures.Future`, in which case the consuming
    operations will simply block until the result is available.

.. note::
    Similarly, an executor can be passed to the function `paragraph.session.apply`.


Eager mode
''''''''''

Within the context manager `paragraph.session.eager_mode`, ops are executed eagerly: the underlying `_run` method is invoked directly rather than
returning an instance of `Variable`. In this mode, arguments of type `Variable` are generally not accepted. No concurrent evaluation occurs in eager
mode.

This mode is particularly useful when testing or debugging a computation graph without modifying the code defining it, by simply bypassing the machinery set
up by the framework.


Backward propagation
''''''''''''''''''''

Conversely, information can be backward propagated through the computation graph using *Requirements*.
Where applicable, an op can implement the `arg_requirements` method that resolves the requirement bearing on each of its arguments given this bearing on its
ouput. This comes in handy e.g. when a particular time range should be available from the output, while rolling operations (such as sum, average,...) are
performed in the graph (or any operation requiring a additional "prefetch" operations from the past).

The `arg_requirements` method receives the requirements bearing on the output variable and the name of a variable argument of the operation, and returns the
requirements that should bear on the said variable argument.

Requirements are substantiated by mixin classes, which add attributes and assume full responsibility for their proper aggregation. They are usually defined in
the same module as the operations using them. Then, a *compound requirements* class is simply defined by:

>>> @attr.s
... class MyRequirements(DateRangeRequirement, DatasetContentsRequirement):
...     pass

A requirement class must define the method `merge(self, other)` that aggregates requirements (more accurately, the requirement attributes it defines) arising
from multiple usages of the same variable. This method should fulfill a small number of properties documented in the base class.

Once all components are in place, requirements can be backpropagated:

>>> reqs = solve_requirements(output=v2, output_requirements=MyRequirements(date_range=ExactRange("2001-01-01", "2001-02-01")))
>>> reqs[v1].date_range  # Holds the backpropagated required date_range


Caveats
=======

Side effects
''''''''''''

The order in which variables are evaluated should not be expected to match the order in which they are defined. As a consequence, it is *not safe* for
operations to change variable arguments *in place* (aka `side effects <https://en.wikipedia.org/wiki/Side_effect_(computer_science)>`_). As Python offers
no mechanism to prevent side-effects, it is the responsibility of the user to ensure that copies are returned instead.

For the very same reasons, operations and graphs should be stateless, as their state sequence would otherwise lie outside of the control of the author of a
computation graph.

Glossary
========

.. glossary::
    variable
        Throughout this module, the term _variable_ should be understood in its mathematical sense. A variable can be unbound, and serve as an input
        placeholder, or bound, and symbolize the result of a certain operation applied to a certain set of arguments, at least one of which is also a variable.

    operation
        An operation (or simply op) relates variables together.

    transitive dependency
        A dependency of a variable is any other variable related to it by an operation. The *transitive* dependencies of a variable are the variables
        whose values enter its own evaluation, i.e. all variables in the union of its dependencies, their own dependencies, and so on until no more
        dependency is found. Together with the initial dependent variable, they form the *computation graph spanned* by the latter.

    boundary
        A boundary is an arbitrary list of variables whose dependencies are excluded from the transitive dependency. The set of unbound variables is a
        canonical boundary associated to the transitive dependencies of all its variables. In the context of this module, it essentially allows to prune
        computation branches whose evaluation is not required.

    traversal
        An ordering of the variables resulting from following the dependency relationships (the edges) of a computation graph. Dependency relationships can
        be excluded by setting a boundary to the traversal.

    forward traversal
        `Depth-first <https://en.wikipedia.org/wiki/Depth-first_search>`_ :term:`traversal` of a computation graph, where every dependent variable occurs after
        all its dependencies. In this order, variables can be evaluated in turn, as the values of their dependencies are resolved before their own
        resolution occurs.

    backward traversal
        `Breadth-first <https://en.wikipedia.org/wiki/Breadth-first_search>`_ :term:`traversal` of a computation graph, where a dependency occurs after all
        the variables depending on it, directly or transitively. In this order, information can be backward propagated through the graph.

Overview
========

othoz-paragraph is a pure Python micro-framework supporting seamless lazy and concurrent evaluation of computation graphs.

In essence, the package allows to write *functional* code directly in Python: statements merely specify relationships among *variables* through *operations*.
Evaluation of any variable given the values of other variables is then de facto:

  - **lazy**: only operations participating in the determination of the requested value are executed,
  - **concurrent**: operations can be executed by a thread pool of arbitrary size.

In addition, relationships among variables can be traversed in both directions, allowing a form of backpropagation of
information through the computation network that would be cumbersome to implement in an imperative manner.

A glossary is provided below, which should clarify most concepts implemented in this module. Note that the usage of some terms may slightly differ from
their standard definitions, reading it through before diving into the code is therefore highly recommended irrespective of the reader's familiarity with the
topic.


Getting started
===============

Computation graphs are `bipartite graphs <https://en.wikipedia.org/wiki/Bipartite_graph>`_, where vertices of a one type, the variables (of type
Variable), are connected together exclusively through vertices of another type, the operations (or simply ops, of type Op).

In *paragraph*, turning a regular Python function into an op is as simple as decorating it:

>>> @op
... def f(a, b):
...     return a * b

The operation can then be applied to objects of both Variable and non-Variable type as follows:

>>> v1 = Variable("v1")
>>> v2 = f(2, v1)

Ops differ from regular Python functions in their behavior upon receiving an argument of type Variable. In such a case, they are not executed,
but instead pack the knowledge required for deferred execution into an instance of Variable, and return this variable.
Then, a variable can be evaluated by invoking the function :func:`othoz.paragraph.session.evaluate` and passing in initialization values for the input
variables alongside the target variable:

>>> value = evaluate([v2], args={v1: 4})


Going further
=============

Partial evaluation
''''''''''''''''''

When the arguments passed onto :func:`othoz.paragraph.session.evaluate` are insufficient to resolve fully an output variable (that is, at least one transitive
dependency of the output variable is left uninitialized), the value returned for the output variable is simply another variable. This new variable has in
general fewer dependencies, for dependencies fully resolved upon evaluation are replaced by their values.


Mapping over inputs
'''''''''''''''''''

The function :func:`othoz.paragraph.session.apply` extends :func:`othoz.paragraph.session.evaluate` to take, in addition, an iterator over input arguments to
the computation graph. It takes advantage of partial evaluation to reduce the number of operations evaluated at each iteration.


Concurrency
'''''''''''

Building upon the guarantees granted by a forward traversal, concurrent execution of ops comes at no additional cost. This feature relies on the `concurrent`
package from the Python standard library: ops are simply submitted to an instance of :class:`concurrent.futures.Executor` for evaluation. The executor should
be provided externally and allow calling :class:`concurrent.futures.Future` methods from a submitted callable (in particular, this excludes
:class:`concurrent.futures.ProcessPoolExecutor`). The responsibility for shutting down the executor properly lies on the user. In absence of an executor,
variables are evaluated in a sequential manner, yet still lazily.

Should an operation be executed in the main process, it can be marked as such by setting the attribute `Op.thread_safe` to False.

Example usage:

>>> ...graph definition...
>>> with ThreadPoolExecutor() as ex:
...     res = evaluate([output], args={input: input_value}, executor=ex)

.. note::
    Argument values passed onto :func:`othoz.paragraph.session.evaluate` can be of type :class:`concurrent.futures.Future`, in which case the consuming
    operations will simply block until the result is available.

.. note::
    Similarly, an executor can be passed onto the function :func:`othoz.paragraph.session.apply`.


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


Development Environment Setup
=============================

Running the code in the repository requires that you have set up your
computer according to the standard Othoz development setup (conda, gcloud, …),
see `Handbook V: Production + Development Infrastructure <https://docs.google.com/document/d/1yxAtV9DCNeiYpSIJF_iChZKd60XdGQfoKV6GiY07wJM/edit#heading=h.7z9b4drr2v0u>`_.

Contribution guidelines
=======================

* Writing tests: All code is tested via unittests. Write additional integration tests if necessary
* Code review: Use Bitbucket pull-requests to submit changes to this repository.


Whom do I talk to?
==================

* Preferably use Slack to talk to bourguignon@othoz.com, richter@othoz.com or eitz@othoz.com
* Repo owner or admin: bourguignon@othoz.com


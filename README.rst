Overview
========

othoz-paragraph is a pure Python micro-framework supporting seamless lazy and parallel evaluation and parallelism of computation graphs.

In essence, this package allows to write *functional* code in Python, whose actual execution is deferred, lazy and parallel, by relating *variables* whose
values may not be known before execution time. Such constructs come in handy under the following cumulative conditions:

    - the code expresses stable yet complex, computation or IO intensive dependencies among a number of variables,
    - common use cases require the evaluation of arbitrary subsets of these variables, the content of this subset being versatile and a priori unknown.

Under these conditions, the joint benefits of lazy and parallel evaluation balance the additional programming effort, since intermediate variables necessary to
compute the requested results are automatically discovered and evaluated. Any computation branch that does not contribute to determining the value of the
requested variable is not executed. In addition, relationships among variables can be traversed in both directions, allowing a form of backpropagation of
information through the computation network that would be otherwise cumbersome to implement in an imperative manner.

A glossary is provided below, which should clarify most concepts implemented in this module. Note that the usage of some terms may slightly differ from
their standard definitions, reading it through before diving into the code is therefore highly recommended irrespective of the reader's familiarity with the
topic.


Getting started
===============

Computation graphs are `bipartite graphs <https://en.wikipedia.org/wiki/Bipartite_graph>`_, where vertices of a one type, the variables (of type
Variable), are connected together exclusively through vertices of another type, the operations (or simply ops, of type Op).

Turning a regular Python function into an op is as simple as decorating it:

>>> @op
... def f(a, b):
...     return a * b

The operation can then be applied to objects of both Variable and non-Variable type as follows:

>>> v1 = Variable()
>>> v2 = f(a=2, b=v1)

Ops differ from regular Python functions in their behavior upon receiving an argument of type Variable. In such a case, they are not executed,
but instead pack the knowledge required for deferred execution into an instance of Variable, and return this variable.
Then, a variable can be evaluated by invoking the :func:`evaluate` function and passing in initialization values for the input variables alongside the target
variable:

>>> evaluate(v2, args={v1: 4})

Graphs can be used to compose ops in a modular manner as follows:

>>> import string
>>> @attr.s
>>> class RepeatWord(Op):
...     n = attr.ib(type=int, validator=instance_of(int))
...
...     def _run(self, word):
...         return ", ".join([word] * self.n)
...
>>> upper = op(string.capwords)
>>> @attr.s
>>> class CapitalizeAndRepeat(Graph):
...     word = attr.ib(type=Variable, init=False, factory=Variable)
...     output = attr.ib(type=Variable, init=False, factory=Variable)
...
...     def _build(self):
...         repeater = RepeatWord(2)
...
...         self.word = Variable()
...         up_word = upper(s=self.word)
...
...         self.output = repeater(word=up_word)
...
>>> g = CapitalizeAndRepeat()
>>> evaluate(g.output, args={g.word: "word"})

Note that classes defining Graphs may define the relationships among their attributes in any arbitrary manner, provided no cyclic dependency occurs among
them. In particular, Graphs can have multiple outputs.

Piecing together Graphs into larger ones goes like this:

>>> g1 = CapitalizeAndRepeat()
>>> g2 = CapitalizeAndRepeat()
>>> g2.input = g1.output
>>> evaluate(g2.output, args={g1.word: "word"})


Additional features
===================

Parallel execution
''''''''''''''''''

Building upon the guarantees granted by a forward traversal, parallel execution of ops comes at no additional cost. This feature relies on the `concurrent`
package from the Python standard library: ops are simply submitted to a thread pool for evaluation.

By default, a single thread is used to exclude pitfalls stemming from thread unsafe computations. Provided all operations are thread-safe, setting `max_workers`
to some value is all it takes to take full advantage of this feature.

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

>>> reqs = solve_requirements(output=g2.output, output_requirements=MyRequirements(date_range=ExactRange("2001-01-01", "2001-02-01")))
>>> reqs[g1.input].date_range  # Holds the backpropagated required date_range


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
"""

Development Environment Setup
=============================

Running the code in the repository requires that you have set up your
computer according to the standard Othoz development setup (conda, gcloud, …),
see `Handbook V: Production + Development Infrastructure <https://docs.google.com/document/d/1yxAtV9DCNeiYpSIJF_iChZKd60XdGQfoKV6GiY07wJM/edit#heading=h.7z9b4drr2v0u>`_.

Contribution guidelines
=======================

* Writing tests: All code is tested via unittests. Write additional integration tests if necessary
* Code review: Use Bitbucket pull-requests to submit changes to this repository.


Who do I talk to?
=================

* Preferably use Slack to talk to bourguignon@othoz.com, richter@othoz.com or eitz@othoz.com
* Repo owner or admin: bourguignon@othoz.com


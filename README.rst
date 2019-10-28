Paragraph
=========

A pure Python micro-framework supporting seamless lazy and concurrent evaluation of computation graphs.

.. image:: https://img.shields.io/pypi/v/paragraph.svg
    :target: https://pypi.org/project/paragraph/

.. image:: https://img.shields.io/pypi/pyversions/paragraph.svg
    :target: https://pypi.org/project/paragraph/

.. image:: https://travis-ci.org/Othoz/paragraph.svg?branch=master
    :target: https://travis-ci.org/Othoz/paragraph

.. image:: https://readthedocs.org/projects/paragraph/badge/?version=latest
    :target: https://paragraph.readthedocs.io/en/latest/?badge=latest

.. image:: https://api.codacy.com/project/badge/Coverage/ab1bc36d3b4f44ea9d88b9e608f39aba
    :target: https://www.codacy.com/manual/Othoz/paragraph?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/paragraph&amp;utm_campaign=Badge_Coverage

.. image:: https://api.codacy.com/project/badge/Grade/ab1bc36d3b4f44ea9d88b9e608f39aba
    :target: https://www.codacy.com/manual/Othoz/paragraph?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/paragraph&amp;utm_campaign=Badge_Grade


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
Then, a variable can be evaluated by invoking the function `paragraph.session.evaluate` and passing in initialization values for the input
variables alongside the target variable:

>>> value = evaluate([v2], args={v1: 4})


Going further
=============

For more information please consult the `documentation <http://paragraph.readthedocs.io>`_.

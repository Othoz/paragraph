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


Introduction
''''''''''''

Paragraph is a minimal layer on top of Python to write *functional* code as transparently as possible. One additional class, ``Variable``, and a
function decorator, ``op``, is all it takes to turn a block of regular Python code into a system of equations relating variables:

>>> import paragraph as pg
>>> import operator
>>> x, y = pg.types.Variable("x"), pg.types.Variable("y")
>>> plus = pg.types.op(operator.add())
>>> z = plus(x, y)


The few lines above fully instantiate a *computation graph*, i.e. a computer representation of a system of equations. Here in its simplest form, with just one
equation, relating ``x``, ``y`` and ``z`` via the function ``plus``. Given values for the input variables ``x`` and ``y``, the value of ``z`` is resolved as
follows:

>>> pg.session.evaluate([z], {x: 5, y: 10})
[15]


Key features
''''''''''''

The main benefits of using paragraph stem from the following features of ``pg.session.evaluate``:

Lazy evaluation
  Irrespective of the size of the computation graph, only the operations required to evaluate the output variables are executed.

Eager currying
  Invoking an op with invariable arguments (that is, arguments that are not of type ``Variable``), an op will just return an invariable value: evaluation is
  eager whenever possible. If at least one of the inputs is a variable, say ``t``, ``evaluate`` returns a new variable:
  
  >>> t = Variable("f")
  >>> z_t_10 = pg.evaluate([z], {x: t, y: 10})
  
  Here, ``z_t_10`` is a different variable from ``z``: it depends on a single input variable (``t``), and it knows nothing about a variable ``y``, instead
  storing a reference to the input value ``10``. Thus, ``pg.session.evaluate`` acts much as ``functools.partial``, except it simplifies the system of
  equations where possible.

Transparent multithreading
  Invoking ``evaluate`` with an instance of ``concurrent.ThreadPoolExecutor`` will allow independent blocks of the computation graph to run in separate threads:

  >>> with ThreadPoolExecutor as ex:
  ...     res = pg.evaluate([z_t_10], {t: 5}, ex)

  This is particularly beneficial if large subsets of the graph are independent.


Constraints
'''''''''''

The features listed above come at some price, essentially because the order in which operations are actually executed generally differs from the order of
their invocations. For paragraph to guarantee that a variable always evaluates to the same value given the same inputs, as in a system of mathematical
equations, it is paramount that operations **never** mutate an object they received as an argument, or store as an attribute. The evolution of the state of
the object would be, by definition, out of the control of the programmer. There is close to nothing paragraph can do to prevent such a thing happening. When
in doubt, make sure to operate on a copy of the argument.


Typing
------

Variables make strictly no assumption about the type of their value. However, an op retains the annotations of the underlying function so that types should be
correctly hinted when invoking ops to define variables. The same goes for type checkers.


For more information please consult the `documentation <http://paragraph.readthedocs.io>`_.

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

.. image:: https://api.codacy.com/project/badge/Coverage/9797bcf310104a38ab46098d366d9606
    :target: https://www.codacy.com/manual/Othoz/paragraph?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/paragraph&amp;utm_campaign=Badge_Coverage

.. image:: https://api.codacy.com/project/badge/Grade/9797bcf310104a38ab46098d366d9606
    :target: https://www.codacy.com/manual/Othoz/paragraph?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/paragraph&amp;utm_campaign=Badge_Grade


Introduction
''''''''''''

Paragraph adds the *functional programming paradigm* to Python in a minimal and almost seamless fashion. One additional class, ``Variable``, and a
function decorator, ``op``, is all it takes to turn regular Python code into a *computation graph*, i.e. a computer representation of a system of
equations:

>>> import paragraph as pg
>>> import operator
>>> x, y = pg.Variable("x"), pg.Variable("y")
>>> add = pg.op(operator.add())
>>> s = add.op(x, y)


The few lines above fully instantiate a computation graph, here in its simplest form with just one equation relating ``x``, ``y`` and ``s`` via the function
``add``. Given values for the input variables ``x`` and ``y``, the value of ``s`` is resolved as follows:

>>> pg.evaluate([s], {x: 5, y: 10})
[15]


Key features
''''''''''''

The main benefits of using paragraph stem from the following features of ``pg.session.evaluate``:

Lazy evaluation
  Irrespective of the size of the computation graph, only the operations required to evaluate the output variables are executed. Consider the following
  extension of the above graph:

  >>> z = pg.Variable("z")
  >>> t = add.op(y, z)

  Then the statement:

  >>> pg.evaluate([t], {y: 10, z: 50})
  [60]

  just ignores the variables ``s`` and ``x`` altogether, since they do not contribute to the evaluation of ``t``. In particular, the operation ``add(x, y)``
  is not executed.


Eager currying
  Invoking an op with invariable arguments (that is, arguments that are not of type ``Variable``) just returns an invariable value: evaluation is
  eager whenever possible. If only a subset of inputs is a variable, say ``x_p``, the computation graph can be simplified using ``solve``, which returns a new
  variable:
  
  >>> x_p = Variable("x_p")
  >>> u = add.op(s, t)
  >>> u_xp = pg.solve([u], {x: x_p, y: 10, z: 50})[0]
  
  Here, ``u_xp`` is a different variable from ``u``: it depends on a single input variable (``x_p``), and it knows nothing about a variable ``y`` or ``z``,
  instead storing a reference to the value of their sum ``t``, i.e. ``60``.

  Thus, ``pg.session.solve`` acts much as ``functools.partial``, except it simplifies the system of equations where possible by executing dependent
  operations whose arguments are invariable.

Transparent multithreading
  Invoking ``evaluate`` or ``solve`` with an instance of ``concurrent.ThreadPoolExecutor`` will allow independent blocks of the computation graph to run in
  separate threads:

  >>> with ThreadPoolExecutor as ex:
  ...     res = pg.evaluate([z_t], {t: 5}, ex)

  This is particularly beneficial if large subsets of the graph are independent.


Constraints
'''''''''''

Side-effects
------------

The features listed above come at some price, essentially because the order in which operations are actually executed generally differs from the order of
their invocations. For paragraph to guarantee that a variable always evaluates to the same value given the same inputs, as in a system of mathematical
equations, it is paramount that operations remain free of side-effects, i.e. they **never** mutate an object they received as an argument, or store as an
attribute. The state sequence of the object would be, by definition, out of the control of the programmer.

There is close to nothing paragraph can do to prevent such a thing happening. When in doubt, make sure to operate on a copy of the argument.

Typing
------

Variables do not carry any information regarding the type of the value they represent, which precludes binding a method of the underlying value to an
instance of ``Variable``: such instructions can appear only within the code of an op. Since binary operators are implemented using special methods in
Python, this also precludes such statements as:

>>> s = x + y

for this would be resolved by the Python interpreter into ``s = x.__add__(y)``, then ``s = y.__radd__(x)``, yet none of these methods is defined by
``Variable``.

For more information please consult the `documentation <http://paragraph.readthedocs.io>`_.

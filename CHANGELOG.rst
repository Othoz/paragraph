Versions
========

The format is based on `Keep a Changelog <http://keepachangelog.com/en/1.0.0/>`_
and this project adheres to `Semantic Versioning <http://semver.org/spec/v2.0.0.html>`_.

All release versions should be documented here with release date and types of changes.
Unreleased changes and pre-releases (i.e. alpha/beta versions) can be documented under the section Unreleased.

Possible types of changes are:

- ``Added`` for new features
- ``Changed`` for changes in existing functionality
- ``Deprecated`` for soon-to-be removed features
- ``Removed`` for now removed features
- ``Fixed`` for any bug fixes
- ``Security`` in case of vulnerabilities

0.3.1 (unreleased)
------------------

Added
'''''
- eager mode using the eponymous context manager in session.py


0.3.0 - 23.10.2019
------------------

Changed
'''''''
- Positional arguments are now allowed when invoking ops
- An executor has to be provided externally for parallel execution to take place.
- `Op.__call__` now accepts inputs of type `concurrent.futures.Future`.
- completely remove the concept of boundary, which opens the door to inconsistent behavior. Instead, only independent variables can be initialized for
  evaluation.
- instances of `Variable` now hold a reference to the generating op in place of the forward and backward callables
- instances of `Variable` and `Op` now have a useful string representation

Fixed
'''''
- evaluating a graph without initializing an input variable (that is, a variable without dependencies) would result in calling None, which is not callable.

0.2.0 - 15.10.2019
------------------

Changed
'''''''
- all algorithms now work on a list of output variables, not a single one

Removed
'''''''
- class `othoz.paragraph.types.Graph`, as it does not add to the functionality of the framework


0.1.0 - 09.10.2019
------------------

Added
'''''
- repository skeleton
- initial version of source code
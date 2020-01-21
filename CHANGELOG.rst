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


Unreleased
----------

Deprecated
''''''''''
- support for unresolved output variables in ``session.evaluate``, use ``sessions.solve`` for that purpose
- support for arguments of type Variable in ``Op.__call__``, use ``Op.op`` instead

Changed
'''''''
- simplify ``op`` decorator
- simplify default implementation of ``Op.__repr__``

Added
'''''
- method ``Op.op`` to be used in place of direct invocation of an Op instance when building a graph


1.0.1 - 07.10.2020
------------------

Fixed
'''''
- mistyped variable name breaks ``session.apply``


1.0.0 - 24.10.2019
------------------

Added
'''''
- initial version of source code

# This __init__py has the responsibility to mark the parent folder as the
# common 'othoz' root namespace that we use for all Python libraries
# See https://packaging.python.org/guides/packaging-namespace-packages/
# Note that it appears we are forced to use pkg_resources-style namespace packages
# because otherwise the conda build complains and fails
__import__('pkg_resources').declare_namespace(__name__)
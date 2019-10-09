"""Temporary root level conftest.py for customizing pytest behaviour

In the future we might think of writing a small pytest plugin which replaces `./test` in every repository.
This plugin could set useful default flags, add custom othoz options and automatically detect CI runs.
"""

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("othoz")
    group.addoption("--unit", action="store_true", default=False, help="run only unit tests")
    group.addoption("--integration", action="store_true", default=False, help="run only integration tests")


def pytest_collection_modifyitems(config, items):
    unit = config.getoption("--unit")
    integration = config.getoption("--integration")

    if unit and integration:
        raise ValueError("The flags --unit and --integration are exclusive")

    for item in items:
        if unit and "integration" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="Running unit tests only"))

        if integration and "integration" not in item.keywords:
            item.add_marker(pytest.mark.skip(reason="Running integration tests only"))

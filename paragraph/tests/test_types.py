import pytest
import attr

from unittest.mock import MagicMock

from paragraph.types import op, Op, Variable, Requirement


@attr.s
class MockReq(Requirement):
    _string = attr.ib(type=str, default="")

    def merge(self, other):
        self._string += other._string
        super().merge(other)


def mock_op(name=""):
    class MockOp(Op):
        def __repr__(self):
            return name
        _run = MagicMock(return_value="{}_return_value".format(name))
        arg_requirements = MagicMock(return_value=MockReq("Arg requirement"))

    return MockOp()


class TestVariable:
    @staticmethod
    def test_validator_raises_if_dependent_variable_is_given_a_name():
        with pytest.raises(ValueError):
            _ = Variable("name", dependencies={"a": Variable("name")})

    @staticmethod
    def test_validator_raises_if_independent_variable_is_not_given_a_name():
        with pytest.raises(ValueError):
            _ = Variable()

    @staticmethod
    def test_str_is_correct():
        var = Variable("v1")

        assert str(var) == "v1"


class TestOpDecorator:
    @staticmethod
    def test_invokes_function_if_args_invariable():
        mocked_function = MagicMock(return_value="Return value")
        mocked_operation = op(mocked_function)

        return_value = mocked_operation(a=1, b="b")

        mocked_function.assert_called_once_with(a=1, b="b")
        assert return_value == "Return value"

    @staticmethod
    def test_returns_variable_if_some_arg_variable():
        mocked_function = MagicMock(return_value="Return value")
        mocked_op = op(mocked_function)

        input_var = Variable("input")
        return_var = mocked_op(a=1, b=input_var)

        assert not mocked_function.called
        assert isinstance(return_var, Variable)
        assert return_var.dependencies == {"b": input_var}

    @staticmethod
    def test_string_representation():
        mocked_function = MagicMock(__name__="function")
        mocked_op = op(mocked_function)
        variable = Variable(name="input")

        result = mocked_op(arg=variable)

        assert str(result) == "function(arg=input)"


class TestOpClass:
    @staticmethod
    def test_call_invokes_function_if_args_invariable():
        operation = mock_op("op")
        return_value = operation(a=1, b="b")

        operation._run.assert_called_once_with(a=1, b="b")
        assert return_value == "op_return_value"

    @staticmethod
    def test_call_returns_variable_if_some_arg_variable():
        operation = mock_op("op")
        input_var = Variable("input")
        return_var = operation(a=1, b=input_var)

        assert not operation._run.called
        assert isinstance(return_var, Variable)
        assert return_var.dependencies == {"b": input_var}

    @staticmethod
    def test_returned_variable_has_correct_name():
        operation = mock_op("op")
        variable = Variable(name="input")
        result = operation(arg=variable)

        assert str(result) == "op(arg=input)"

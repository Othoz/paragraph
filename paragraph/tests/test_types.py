import pytest
import attr

from unittest.mock import MagicMock

from paragraph.types import Op, op, Variable, Requirement


@attr.s
class MockReq(Requirement):
    _string = attr.ib(type=str, default="")

    def merge(self, other):
        self._string += other._string
        super().merge(other)


def mock_op(name="") -> Op:
    operation = op(MagicMock(__name__=name, return_value=f"{name}_return_value"))
    operation.arg_requirements = MagicMock(return_value=MockReq("Arg requirement"))

    return operation


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
    def test_str_is_correct_for_independent_variable():
        var = Variable("v1")

        assert str(var) == "v1"

    @staticmethod
    def test_str_is_correct_for_dependent_variable():
        v1 = Variable("v1")
        v2 = Variable("v2")
        v3 = mock_op("op").op(v1, kw1=v2)

        assert str(v3) == "op(v1, kw1=v2)"

    @staticmethod
    def test_is_input_correct_for_independent_variable():
        v1 = Variable("v1")
        assert v1.isinput()

    @staticmethod
    def test_is_input_correct_for_dependent_variable():
        v1 = Variable("v1")
        op = mock_op("op")
        v2 = op.op(v1)
        assert not v2.isinput()
        v2 = op.op(1)
        assert not v2.isinput()


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

        result = mocked_op.op(arg=variable)

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
    def test_invocation_warns_on_variable_argument():
        operation = mock_op("op")
        with pytest.deprecated_call():
            operation(Variable("v"), 0)

    @staticmethod
    def test_returned_variable_has_correct_name():
        operation = mock_op("op")
        variable = Variable(name="input")
        result = operation.op(arg=variable)

        assert str(result) == "op(arg=input)"

    @staticmethod
    def test_invocation_warns_not_on_invariable_argument():
        operation = mock_op("op")
        with pytest.warns(None) as record:
            operation(0, 0)

        assert len(record) == 0

    @staticmethod
    @pytest.mark.parametrize("argument",
                             [pytest.param(0, id="Non-variable argument"),
                              pytest.param(Variable("v"), id="Variable argument")])
    def test_op_method_always_returns_a_variable_instance(argument):
        operation = mock_op("op")
        result = operation.op(argument)

        assert isinstance(result, Variable)

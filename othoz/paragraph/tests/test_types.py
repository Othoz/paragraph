from unittest.mock import MagicMock, patch
import attr

from othoz.paragraph.types import op, Op, Variable, Requirement


@attr.s
class TestReq(Requirement):
    _string = attr.ib(type=str, default="")

    def merge(self, other):
        self._string += other._string
        super().merge(other)


def mock_op():
    class MockOp(Op):
        _run = MagicMock(return_value="Return value")
        _arg_requirements = MagicMock(return_value=TestReq("Arg requirement"))

    return MockOp()


class TestVariable:
    def test_default_func_returns_self(self):
        var = Variable()
        
        assert var.func() is var

class TestOpDecorator:
    def test_invokes_function_if_args_invariable(self):
        mocked_function = MagicMock(return_value="Return value")
        mocked_operation = op(mocked_function)

        return_value = mocked_operation(a=1, b="b")

        mocked_function.assert_called_once_with(a=1, b="b")
        assert return_value == "Return value"

    def test_returns_variable_if_some_arg_variable(self):
        mocked_function = MagicMock(return_value="Return value")
        mocked_op = op(mocked_function)

        input_var = Variable()
        return_var = mocked_op(a=1, b=input_var)

        assert not mocked_function.called
        assert isinstance(return_var, Variable)
        assert return_var.dependencies == {"b": input_var}


class TestOpClass:
    def test_call_invokes_function_if_args_invariable(self):
        with patch.multiple("othoz.paragraph.types.Op", __abstractmethods__=set(), _run=MagicMock(return_value="Return value")):
            operation = Op()
            return_value = operation(a=1, b="b")

            operation._run.assert_called_once_with(a=1, b="b")
            assert return_value == "Return value"

    def test_call_returns_variable_if_some_arg_variable(self):
        with patch.multiple("othoz.paragraph.types.Op", __abstractmethods__=set(), _run=MagicMock(return_value="Return value")):
            operation = Op()
            input_var = Variable()
            return_var = operation(a=1, b=input_var)

            assert not Op._run.called
            assert isinstance(return_var, Variable)
            assert return_var.dependencies == {"b": input_var}

    def test_call_writes_requirements_update_func(self):
        operation = mock_op()
        input_var = Variable()
        return_var = operation(a=1, b=input_var)

        assert return_var.arg_requirements_func == operation._arg_requirements
        assert input_var.arg_requirements_func("Output requirements", "some_arg") == ""

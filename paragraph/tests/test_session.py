import pytest

from concurrent.futures.thread import ThreadPoolExecutor

from paragraph.types import Variable
from paragraph.session import eager_mode, traverse_fw, traverse_bw, evaluate, solve_requirements, apply, solve
from paragraph.tests.test_types import MockReq, mock_op


@pytest.fixture
def graph():
    graph = lambda: None  # noqa: E731
    op0 = mock_op("op0")
    graph.input = Variable("input")
    output0 = op0(arg=graph.input)
    op1 = mock_op("op1")
    output1 = op1(graph.input, arg1=output0)

    graph.output = [output0, output1]

    return graph


@pytest.fixture
def thread_pool_executor():
    with ThreadPoolExecutor() as executor:
        yield executor


def test_no_variable_returned_in_eager_mode():
    with eager_mode():
        op0 = mock_op("op0")
        input = "input_value"
        output0 = op0(arg=input)
        op0._run.assert_called_once_with(arg=input)
        assert output0 == "op0_return_value"
        op1 = mock_op("op1")
        output1 = op1(input, arg1=output0)
        op1._run.assert_called_once_with(input, arg1="op0_return_value")
        assert output1 == "op1_return_value"


class TestForwardGenerator:
    @staticmethod
    def test_generated_values(graph):
        items = list(traverse_fw(graph.output))
        expected = [graph.input] + graph.output

        assert items == expected


class TestBackwardGenerator:
    @staticmethod
    def test_generated_value_wo_boundary(graph):
        items = list(traverse_bw(graph.output))
        expected = [graph.output[1], graph.output[0], graph.input]

        assert items == expected


class TestEvaluate:
    @staticmethod
    def test_sequential_evaluation_is_correct(graph):
        res = evaluate(graph.output, args={graph.input: "input_value"})

        assert res[0] == "op0_return_value"
        assert res[1] == "op1_return_value"

        graph.output[0].op._run.assert_called_once_with(arg="input_value")
        graph.output[1].op._run.assert_called_once_with("input_value", arg1="op0_return_value")

    @staticmethod
    def test_parallel_evaluation_is_correct(graph, thread_pool_executor):
        res = evaluate(graph.output, args={graph.input: "input_value"}, executor=thread_pool_executor)

        assert res[0] == "op0_return_value"
        assert res[1] == "op1_return_value"

        graph.output[0].op._run.assert_called_once_with(arg="input_value")
        graph.output[1].op._run.assert_called_once_with("input_value", arg1="op0_return_value")

    @staticmethod
    def test_evaluation_is_lazy(graph):
        res = evaluate([graph.output[0]], args={graph.input: "input_value"})
        operation = graph.output[1].op

        assert res[0] == "op0_return_value"
        assert not operation._run.called

    @staticmethod
    def test_deprecation_if_evaluating_with_incomplete_arguments(graph):
        with pytest.deprecated_call():
            _ = evaluate([graph.output[0]], args={})

    @staticmethod
    def test_no_deprecation_if_evaluating_with_complete_arguments(graph):
        with pytest.warns(None) as record:
            _ = evaluate([graph.output[0]], args={graph.input: 0})

        assert len(record) == 0


class TestSolve:
    @staticmethod
    def test_sequential_solve_is_correct(graph):
        res = solve(graph.output, args={graph.input: "input_value"})

        assert isinstance(res[0], Variable)
        assert res[0].args == {"arg": "input_value"}
        assert res[0].dependencies == {}
        assert isinstance(res[1], Variable)
        assert res[1].args == {0: "input_value"}
        assert res[1].dependencies == {"arg1": res[0]}

        graph.output[0].op._run.assert_not_called()
        graph.output[1].op._run.assert_not_called()

    @staticmethod
    def test_parallel_solve_is_correct(graph, thread_pool_executor):
        res = solve(graph.output, args={graph.input: "input_value"}, executor=thread_pool_executor)

        assert isinstance(res[0], Variable)
        assert res[0].args == {"arg": "input_value"}
        assert res[0].dependencies == {}
        assert isinstance(res[1], Variable)
        assert res[1].args == {0: "input_value"}
        assert res[1].dependencies == {"arg1": res[0]}

        graph.output[0].op._run.assert_not_called()
        graph.output[1].op._run.assert_not_called()

    @staticmethod
    def test_solve_is_lazy(graph):
        _ = evaluate([graph.output[0]], args={graph.input: "input_value"})
        operation = graph.output[1].op

        assert not operation._run.called


class TestApply:
    @staticmethod
    def test_sequential_apply_returns_correct_number_of_results(graph):
        res = list(apply(graph.output, args={}, iter_args=[{graph.input: "input_value"}] * 5))

        assert len(res) == 5

    @staticmethod
    def test_parallel_apply_returns_correct_number_of_results(graph, thread_pool_executor):
        res = list(apply(graph.output, args={}, iter_args=[{graph.input: "input_value"}] * 5, executor=thread_pool_executor))

        assert len(res) == 5

    @staticmethod
    def test_parallel_apply_raises_on_overwriting_an_input_variable(graph, thread_pool_executor):
        with pytest.raises(ValueError):
            list(apply(graph.output, args={graph.input: "input_value"}, iter_args=[{graph.input: "input_value"}] * 5, executor=thread_pool_executor))


class TestRequirementSolving:
    @staticmethod
    def test_req_update_func_called():
        operation = mock_op("op")

        var = Variable("input")
        res = operation(a=1, b=var)

        output_req = MockReq("Output requirement")
        reqs = solve_requirements(output_requirements={res: output_req})

        expected = {res: output_req, var: MockReq("Arg requirement")}

        assert reqs == expected
        res.op.arg_requirements.assert_called_once_with(output_req, "b")

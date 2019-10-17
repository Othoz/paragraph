import pytest

from othoz.paragraph.types import Variable
from othoz.paragraph.session import traverse_fw, traverse_bw, evaluate, solve_requirements, apply
from othoz.paragraph.tests.test_types import MockReq, mock_op


@pytest.fixture
def graph():
    graph = lambda: None  # noqa: E731
    op1 = mock_op("op0")
    graph.input = Variable("input")
    output0 = op1(arg=graph.input)

    op2 = mock_op("op1")
    output1 = op2(arg0=graph.input, arg1=output0)

    graph.output = [output0, output1]

    return graph


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


@pytest.mark.parametrize("max_workers", [pytest.param(1, id="Single thread"),
                                         pytest.param(50, id="Multi-threaded")])
class TestEvaluate:
    @staticmethod
    def test_variable_evaluation_is_correct(graph, max_workers):
        res = evaluate(graph.output, args={graph.input: "Input value"}, max_workers=max_workers)

        assert res[0] == "op0 return value"
        assert res[1] == "op1 return value"

        graph.output[0].op._run.assert_called_once_with(arg="Input value")
        graph.output[1].op._run.assert_called_once_with(arg0="Input value", arg1="op0 return value")

    @staticmethod
    def test_evaluation_is_lazy(graph, max_workers):
        res = evaluate([graph.output[0]], args={graph.input: "Input value"}, max_workers=max_workers)
        operation = graph.output[1].op

        assert res[0] == "op0 return value"
        assert not operation._run.called


@pytest.mark.parametrize("max_workers", [pytest.param(1, id="Single thread"),
                                         pytest.param(50, id="Multi-threaded")])
class TestApply:
    @staticmethod
    def test_apply_returns_correct_number_of_results(graph, max_workers):
        res = list(apply(graph.output, args={}, iter_args=[{graph.input: "Input value"}] * 5, max_workers=max_workers))

        assert len(res) == 5

    @staticmethod
    def test_apply_raises_on_overwriting_an_input_variable(graph, max_workers):
        with pytest.raises(ValueError):
            list(apply(graph.output, args={graph.input: "Input value"}, iter_args=[{graph.input: "Input value"}] * 5, max_workers=max_workers))


class TestRequirementSolving:
    @staticmethod
    def test_req_update_func_called():
        operation = mock_op()

        var = Variable("input")
        res = operation(a=1, b=var)

        output_req = MockReq("Output requirement")
        reqs = solve_requirements(output_requirements={res: output_req})

        expected = {res: output_req, var: MockReq("Arg requirement")}

        assert reqs == expected
        res.op.arg_requirements.assert_called_once_with(output_req, "b")

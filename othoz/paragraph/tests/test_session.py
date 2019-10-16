import pytest

from othoz.paragraph.types import Variable
from othoz.paragraph.session import traverse_fw, traverse_bw, evaluate, solve_requirements, apply
from othoz.paragraph.tests.test_types import TestReq, mock_op


@pytest.fixture
def graph():
    graph = lambda: None  # noqa: E731
    op1 = mock_op("op0")
    graph.input = Variable()
    output0 = op1(arg=graph.input)

    op2 = mock_op("op1")
    output1 = op2(arg0=graph.input, arg1=output0)

    graph.output = [output0, output1]

    return graph


class TestForwardGenerator:
    def test_generated_values_wo_boundary(self, graph):
        items = list(traverse_fw(graph.output))
        expected = [graph.input] + graph.output

        assert items == expected

    def test_generated_values_with_boundary(self, graph):
        items = list(traverse_fw(graph.output, boundary=[graph.input]))
        expected = graph.output

        assert items == expected


class TestBackwardGenerator:
    def test_generated_value_wo_boundary(self, graph):
        items = list(traverse_bw(graph.output))
        expected = [graph.output[1], graph.output[0], graph.input]

        assert items == expected

    def test_generated_values_with_boundary(self, graph):
        items = list(traverse_bw(graph.output, boundary=[graph.input]))

        assert items == [graph.output[1], graph.output[0]]


@pytest.mark.parametrize("max_workers", [pytest.param(1, id="Single thread"),
                                         pytest.param(50, id="Multi-threaded")])
class TestEvaluate:
    def test_variable_evaluation_is_correct(self, graph, max_workers):
        res = evaluate(graph.output, args={graph.input: "Input value"}, max_workers=max_workers)

        assert res[0] == "op0 return value"
        assert res[1] == "op1 return value"

        graph.output[0].func.func._run.assert_called_once_with(arg="Input value")
        graph.output[1].func.func._run.assert_called_once_with(arg0="Input value", arg1="op0 return value")

    def test_evaluation_is_lazy(self, graph, max_workers):
        res = evaluate([graph.output[0]], args={graph.output[0]: "Input value"}, max_workers=max_workers)
        operation = graph.output[0].func.func

        assert res[0] == "Input value"
        assert not operation._run.called


@pytest.mark.parametrize("max_workers", [pytest.param(1, id="Single thread"),
                                         pytest.param(50, id="Multi-threaded")])
class TestApply:
    def test_apply_returns_correct_number_of_results(self, graph, max_workers):
        res = list(apply(graph.output, args={}, iter_args=[{graph.output[0]: "Input value"}] * 5, max_workers=max_workers))

        assert len(res) == 5

    def test_apply_raises_on_overwriting_a_resolved_variable(self, graph, max_workers):
        with pytest.raises(ValueError):
            list(apply(graph.output, args={graph.input: "Input value"}, iter_args=[{graph.output[0]: "Input value"}] * 5, max_workers=max_workers))

class TestRequirementSolving:
    def test_req_update_func_called(self):
        operation = mock_op("")

        var = Variable()
        res = operation(a=1, b=var)

        output_req = TestReq("Output requirement")
        reqs = solve_requirements(output_requirements={res: output_req})

        expected = {res: output_req, var: TestReq("Arg requirement")}

        assert reqs == expected
        res.arg_requirements_func.assert_called_once_with(output_req, "b")

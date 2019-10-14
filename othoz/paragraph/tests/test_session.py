import pytest
import attr
from unittest.mock import MagicMock

from othoz.paragraph.types import Requirement, Variable, Op
from othoz.paragraph.session import traverse_fw, traverse_bw, evaluate, solve_requirements


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


@pytest.fixture
def graph():
    graph = lambda: None  # noqa: E731
    op1 = mock_op()
    graph.input = Variable()
    output1 = op1(arg=graph.input)

    op2 = mock_op()
    output2 = op2(arg=graph.input)

    graph.output = [output1, output2]

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
        expected = graph.output + [graph.input]

        assert items == expected

    def test_generated_values_with_boundary(self, graph):
        items = list(traverse_bw(graph.output, boundary=[graph.input]))

        assert items == graph.output


@pytest.mark.parametrize("max_workers", [pytest.param(1, id="Single thread"),
                                         pytest.param(50, id="Multi-threaded")])
class TestEvaluation:
    def test_variable_evaluation_is_correct(self, graph, max_workers):
        res = evaluate(graph.output, args={graph.input: "Input value"}, max_workers=max_workers)

        assert res[0] == "Return value"
        for var in graph.output:
            var.func.func._run.assert_called_once_with(arg="Input value")

    def test_evaluation_is_lazy(self, graph, max_workers):
        res = evaluate([graph.output[0]], args={graph.output[0]: "Input value"}, max_workers=max_workers)
        operation = graph.output[0].func.func

        assert res[0] == "Input value"
        assert not operation._run.called


class TestRequirementSolving:
    def test_req_update_func_called(self):
        operation = mock_op()

        var = Variable()
        res = operation(a=1, b=var)

        output_req = TestReq("Output requirement")
        reqs = solve_requirements(output_requirements={res: output_req})

        expected = {res: output_req, var: TestReq("Arg requirement")}

        assert reqs == expected
        res.arg_requirements_func.assert_called_once_with(output_req, "b")

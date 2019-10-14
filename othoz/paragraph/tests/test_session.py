import pytest
import attr
from unittest.mock import MagicMock, patch

from othoz.paragraph.types import Requirement, Variable, Op, Graph
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
def make_graph():
    def _make_graph():
        operation = mock_op()

        with patch.multiple("othoz.paragraph.types.Graph", __abstractmethods__=set(), _build=lambda x: None):
            g = Graph()

            g.input = Variable()
            g.output = operation(arg=g.input)

        return g

    return _make_graph


@pytest.fixture
def graph(make_graph):
    return make_graph()


class TestForwardGenerator:
    def test_generated_values_wo_boundary(self, graph):
        items = list(traverse_fw([graph.output]))
        expected = [graph.input, graph.output]

        assert items == expected

    def test_generated_values_with_boundary(self, graph):
        items = list(traverse_fw([graph.output], boundary=[graph.input]))
        expected = [graph.output]

        assert items == expected

    def test_generator_walks_across_subgraphs(self, make_graph):
        g1 = make_graph()
        g2 = make_graph()
        g2.input = g1.output

        items = list(traverse_fw([g2.output]))
        expected = [g1.input, g1.output, g2.input, g2.output]

        assert items == expected


class TestBackwardGenerator:
    def test_generated_value_wo_boundary(self, graph):
        items = list(traverse_bw([graph.output]))
        expected = [graph.output, graph.input]

        assert items == expected

    def test_generated_values_with_boundary(self, graph):
        items = list(traverse_bw([graph.output], boundary=[graph.input]))

        assert items == [graph.output]

    def test_generator_walks_across_subgraphs(self, make_graph):
        g1 = make_graph()
        g2 = make_graph()
        g2.input = g1.output

        items = list(traverse_bw([g2.output]))
        expected = [g2.output, g2.input, g1.output, g1.input]

        assert items == expected


@pytest.mark.parametrize("max_workers", [pytest.param(1, id="Single thread"),
                                         pytest.param(50, id="Multi-threaded")])
class TestEvaluation:
    def test_variable_evaluation_is_correct(self, graph, max_workers):
        res = evaluate([graph.output], args={graph.input: "Input value"})
        operation = graph.output.func.func

        assert res[0] == "Return value"
        operation._run.assert_called_once_with(arg="Input value")

    def test_evaluation_is_lazy(self, graph, max_workers):
        res = evaluate([graph.output], args={graph.output: "Input value"})
        operation = graph.output.func.func

        assert res[0] == "Input value"
        assert not operation._run.called

    def test_evaluation_across_subgraphs(self, make_graph, max_workers):
        g1 = make_graph()
        g2 = make_graph()
        g2.input = g1.output

        res = evaluate([g2.output], args={g1.input: "Input value"})

        assert res[0] == "Return value"
        g1.output.func.func._run.assert_called_once()


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

import pytest
import asyncio
from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import GraphExecutionError
from graphorchestrator.decorators.actions import node_action
from graphorchestrator.nodes.nodes import ProcessingNode
from graphorchestrator.graph.builder import GraphBuilder
from graphorchestrator.graph.executor import GraphExecutor

store = {"flag": 0}
op = {"simple": 0, "delayed_in": 0, "delayed_out": 0}


@node_action
def simple_action(state: State):
    op["simple"] += 1
    return state


@node_action
async def delayed_action(state: State):
    if store["flag"] == 0:
        op["delayed_in"] += 1
        store["flag"] = 1
        await asyncio.sleep(10)
    op["delayed_out"] += 1
    return state


builder = GraphBuilder()
builder.add_node(ProcessingNode("node1", delayed_action))
builder.add_node(ProcessingNode("node2", simple_action))
builder.add_concrete_edge("start", "node1")
builder.add_concrete_edge("node1", "node2")
builder.add_concrete_edge("node2", "end")
graph = builder.build_graph()
initial_state = State(messages=[])


@pytest.fixture(autouse=True)
def reset_globals():
    store["flag"] = 0
    op["simple"] = 0
    op["delayed_in"] = 0
    op["delayed_out"] = 0


@pytest.mark.asyncio
async def test_bad_fallback_configuration():
    initial_state = State(messages=[])
    with pytest.raises(GraphExecutionError):
        executor = GraphExecutor(
            graph, initial_state, allow_fallback_from_checkpoint=True
        )


@pytest.mark.asyncio
async def test_checkpoint_and_graph_fallback():
    executor = GraphExecutor(
        graph,
        initial_state,
        checkpoint_path="testcase_1.pkl",
        checkpoint_every=1,
        allow_fallback_from_checkpoint=True,
    )
    result = await executor.execute(superstep_timeout=4)
    assert op["simple"] == 1
    assert op["delayed_in"] == 1
    assert op["delayed_out"] == 1
    assert store["flag"] == 1


@pytest.mark.asyncio
async def test_timeout_error_raised_without_fallback():
    executor = GraphExecutor(
        graph,
        initial_state,
        checkpoint_path="testcase_2.pkl",
        checkpoint_every=1,
        allow_fallback_from_checkpoint=False,
    )
    with pytest.raises(GraphExecutionError):
        result = await executor.execute(superstep_timeout=4)

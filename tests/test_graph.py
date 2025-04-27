import asyncio
import pytest
import random
from typing import List

# Core
from graphorchestrator.core.state import State
from graphorchestrator.core.retry import RetryPolicy
from graphorchestrator.ai.ai_action import AIActionBase
from graphorchestrator.core.exceptions import (
    DuplicateNodeError,
    NodeNotFoundError,
    EdgeExistsError,
    NodeActionNotDecoratedError,
    RoutingFunctionNotDecoratedError,
    ToolMethodNotDecorated,
    InvalidNodeActionOutput,
    InvalidAggregatorActionError,
    InvalidRoutingFunctionOutput,
    GraphConfigurationError,
    EmptyToolNodeDescriptionError,
    GraphExecutionError,
)

# Decorators
from graphorchestrator.decorators.actions import (
    node_action,
    routing_function,
    tool_method,
    aggregator_action,
)
from graphorchestrator.decorators.builtin_actions import passThrough, selectRandomState

# Nodes and Edges
from graphorchestrator.nodes.nodes import (
    ProcessingNode,
    AggregatorNode,
    ToolNode,
    AINode,
    HumanInTheLoopNode,
)
from graphorchestrator.edges.conditional import ConditionalEdge

# Graph Core
from graphorchestrator.graph.builder import GraphBuilder
from graphorchestrator.graph.executor import GraphExecutor


def test_01_valid_node_action_decorator():
    @node_action
    def valid_func(state):
        return state

    node = ProcessingNode("valid", valid_func)
    assert node.node_id == "valid"


def test_02_missing_node_action_decorator():
    def bad_func(state):
        return state

    with pytest.raises(NodeActionNotDecoratedError):
        ProcessingNode("invalid", bad_func)


def test_03_missing_routing_decorator():
    def router(state):
        _ = state
        return "node3"

    node1 = ProcessingNode("node1", passThrough)
    node2 = ProcessingNode("node2", passThrough)
    node3 = ProcessingNode("node3", passThrough)
    with pytest.raises(RoutingFunctionNotDecoratedError):
        ConditionalEdge(node1, [node2, node3], router)


def test_04_duplicate_node_error():
    builder = GraphBuilder()
    node1 = ProcessingNode("node1", passThrough)
    builder.add_node(node1)
    with pytest.raises(DuplicateNodeError):
        builder.add_node(ProcessingNode("node1", passThrough))


def test_05_add_non_existing_node_on_concrete_edge():
    builder = GraphBuilder()
    node1 = ProcessingNode("node1", passThrough)
    builder.add_node(node1)
    with pytest.raises(NodeNotFoundError):
        builder.add_concrete_edge("node1", "node2")


def test_06_add_non_existing_node_on_conditional_edge():
    @routing_function
    def router(state):
        return "end"

    builder = GraphBuilder()
    node1 = ProcessingNode("node1", passThrough)
    builder.add_node(node1)
    with pytest.raises(NodeNotFoundError):
        builder.add_conditional_edge("node1", ["node2", "end", "start"], router)


def test_07_add_concrete_edge_on_concrete_edge():
    builder = GraphBuilder()
    node1 = ProcessingNode("node1", passThrough)
    node2 = ProcessingNode("node2", passThrough)
    builder.add_node(node1)
    builder.add_node(node2)
    builder.add_concrete_edge("node1", "node2")
    with pytest.raises(EdgeExistsError):
        builder.add_concrete_edge("node1", "node2")


def test_08_add_conditional_edge_on_concrete_edge():
    @routing_function
    def router(state):
        return "end"

    builder = GraphBuilder()
    node1 = ProcessingNode("node1", passThrough)
    node2 = ProcessingNode("node2", passThrough)
    builder.add_node(node1)
    builder.add_node(node2)
    builder.add_concrete_edge("node1", "node2")
    with pytest.raises(EdgeExistsError):
        builder.add_conditional_edge("node1", ["node2", "end"], router)


def test_09_add_concrete_edge_on_conditional_edge():
    @routing_function
    def router(state):
        return "end"

    builder = GraphBuilder()
    node1 = ProcessingNode("node1", passThrough)
    node2 = ProcessingNode("node2", passThrough)
    builder.add_node(node1)
    builder.add_node(node2)
    builder.add_conditional_edge("node1", ["node2", "end"], router)
    with pytest.raises(EdgeExistsError):
        builder.add_concrete_edge("node1", "node2")


def test_10_add_conditional_edge_on_conditional_edge():
    @routing_function
    def router1(state):
        return "end"

    @routing_function
    def router2(state):
        return "node1"

    builder = GraphBuilder()
    node1 = ProcessingNode("node1", passThrough)
    node2 = ProcessingNode("node2", passThrough)
    builder.add_node(node1)
    builder.add_node(node2)
    builder.add_conditional_edge("node1", ["node2", "end"], router1)
    with pytest.raises(EdgeExistsError):
        builder.add_conditional_edge("node1", ["node2", "node1"], router2)


def test_11_graph_config_incoming_concrete_edge_to_start():
    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    with pytest.raises(GraphConfigurationError):
        builder.add_concrete_edge("node1", "start")


def test_12_graph_config_incoming_conditional_edge_to_start():
    @routing_function
    def router(state):
        return "start"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    with pytest.raises(GraphConfigurationError):
        builder.add_conditional_edge("node1", ["node1", "start"], router)


def test_13_graph_config_no_edge_from_start():
    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_concrete_edge("node1", "end")
    with pytest.raises(GraphConfigurationError):
        builder.build_graph()


def test_14_graph_config_conditonal_edge_from_start():
    @routing_function
    def router(state):
        return "node1"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_node(ProcessingNode("node2", passThrough))
    builder.add_node(ProcessingNode("node3", passThrough))
    builder.add_aggregator(AggregatorNode("aggregator1", selectRandomState))
    builder.add_conditional_edge("start", ["node1", "node2"], router)
    builder.add_concrete_edge("node1", "aggregator1")
    builder.add_concrete_edge("node2", "aggregator1")
    builder.add_concrete_edge("aggregator1", "node3")
    builder.add_concrete_edge("node3", "end")
    with pytest.raises(GraphConfigurationError):
        builder.build_graph()


def test_15_graph_config_no_outgoing_concrete_edge_from_end():
    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_concrete_edge("start", "end")
    with pytest.raises(GraphConfigurationError):
        builder.add_concrete_edge("end", "node1")


def test_16_graph_config_no_outgoing_conditional_edge_from_end():
    @routing_function
    def router(state):
        return "node2"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_node(ProcessingNode("node2", passThrough))
    builder.add_concrete_edge("start", "end")
    with pytest.raises(GraphConfigurationError):
        builder.add_conditional_edge("end", ["node1", "node2"], router)


def test_17_graph_config_no_edge_to_end():
    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_concrete_edge("start", "node1")
    with pytest.raises(GraphConfigurationError):
        builder.build_graph()


def test_18_graph_config_conditional_edge_to_end():
    @routing_function
    def router(state):
        return "node1"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_concrete_edge("start", "node1")
    builder.add_conditional_edge("node1", ["node1", "end"], router)


@pytest.mark.asyncio
async def test_19_linear_graph():
    builder = GraphBuilder()

    @node_action
    def node1_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 1
        state.messages.append(latest_state)
        return state

    builder.add_node(ProcessingNode("node1", node1_action))
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("node1", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[1])
    executor = GraphExecutor(graph, initial_state)
    final_state = await executor.execute()
    assert final_state == State(messages=[1, 2])


@pytest.mark.asyncio
async def test_20_single_node_looping():
    builder = GraphBuilder()

    @routing_function
    def router(state: State):
        latest_state = state.messages[-1]
        if latest_state % 10 == 0:
            return "end"
        else:
            return "node1"

    @node_action
    def node1_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 1
        state.messages.append(latest_state)
        return state

    builder.add_node(ProcessingNode("node1", node1_action))
    builder.add_concrete_edge("start", "node1")
    builder.add_conditional_edge("node1", ["node1", "end"], router)
    graph = builder.build_graph()
    initial_state = State(messages=[1])
    executor = GraphExecutor(graph, initial_state)
    final_state = await executor.execute()
    assert final_state == State(messages=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


@pytest.mark.asyncio
async def test_21_two_node_linear():
    builder = GraphBuilder()

    @node_action
    def node1_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 1
        state.messages.append(latest_state)
        return state

    @node_action
    def node2_action(state: State):
        latest_state = state.messages[-1]
        latest_state = latest_state % 2
        state.messages.append(latest_state)
        return state

    builder.add_node(ProcessingNode("node1", node1_action))
    builder.add_node(ProcessingNode("node2", node2_action))
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("node1", "node2")
    builder.add_concrete_edge("node2", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[11])
    exeuctor = GraphExecutor(graph, initial_state)
    final_state = await exeuctor.execute()
    assert final_state == State(messages=[11, 12, 0])


@pytest.mark.asyncio
async def test_22_graph_with_aggregator():
    @node_action
    def node1_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 1
        state.messages.append(latest_state)
        return state

    @node_action
    def node2_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 2
        state.messages.append(latest_state)
        return state

    @node_action
    def node3_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 3
        state.messages.append(latest_state)
        return state

    @aggregator_action
    def agg_action(states: List[State]):
        state1 = states[0]
        state2 = states[1]
        latest_state = state1.messages[-1] + state2.messages[-1]
        state1.messages.append(latest_state)
        return state1

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", node1_action))
    builder.add_node(ProcessingNode("node2", node2_action))
    builder.add_node(ProcessingNode("node3", node3_action))
    builder.add_node(AggregatorNode("agg", agg_action))
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("node1", "node2")
    builder.add_concrete_edge("node1", "node3")
    builder.add_concrete_edge("node2", "agg")
    builder.add_concrete_edge("node3", "agg")
    builder.add_concrete_edge("agg", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[1])
    executor = GraphExecutor(graph, initial_state)
    final_state = await executor.execute()
    assert final_state == State(messages=[1, 2, 4, 9])


@pytest.mark.asyncio
async def test_23_aggregator_with_conditional():
    @node_action
    def node1_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 1
        state.messages.append(latest_state)
        return state

    @node_action
    def node2_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 2
        state.messages.append(latest_state)
        return state

    @node_action
    def node3_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 3
        state.messages.append(latest_state)
        return state

    @node_action
    def node4_action(state: State):
        latest_state = state.messages[-1]
        latest_state += 1
        state.messages.append(latest_state)
        return state

    @routing_function
    def router(state: State):
        latest_state = state.messages[-1]
        if latest_state % 3 == 0:
            return "end"
        else:
            return "node1"

    @aggregator_action
    def agg_action(states: List[State]):
        state1 = states[0]
        state2 = states[1]
        latest_state = state1.messages[-1] + state2.messages[-1]
        state1.messages.append(state2.messages[-1])
        state1.messages.append(latest_state)
        return state1

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", node1_action))
    builder.add_node(ProcessingNode("node2", node2_action))
    builder.add_node(ProcessingNode("node3", node3_action))
    builder.add_node(ProcessingNode("node4", node4_action))
    builder.add_aggregator(AggregatorNode("agg", agg_action))
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("node1", "node2")
    builder.add_concrete_edge("node1", "node3")
    builder.add_concrete_edge("node2", "agg")
    builder.add_concrete_edge("node3", "agg")
    builder.add_concrete_edge("agg", "node4")
    builder.add_conditional_edge("node4", ["node1", "end"], router)
    graph = builder.build_graph()
    initial_state = State(messages=[0])
    executor = GraphExecutor(graph, initial_state)
    final_state = await executor.execute()
    assert final_state == State(messages=[0, 1, 3, 4, 7, 8, 9, 11, 12, 23, 24])


@pytest.mark.asyncio
async def test_24_retry_policy_behavior():
    # Test that a node failing a few times is retried according to the retry policy.
    call_count = [0]

    @node_action
    def flaky_node(state: State):
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("Intentional failure")
        state.messages.append(call_count[0])
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("flaky", flaky_node))
    builder.add_concrete_edge("start", "flaky")
    builder.add_concrete_edge("flaky", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[0])
    executor = GraphExecutor(
        graph,
        initial_state,
        retry_policy=RetryPolicy(max_retries=5, delay=0.1, backoff=1),
    )
    final_state = await executor.execute()
    # Expect that after a few failures, the node eventually appends the call count (which should be 3)
    assert 3 in final_state.messages


@pytest.mark.asyncio
async def test_25_max_supersteps_exceeded():
    # Create a graph that cycles indefinitely (without reaching "end") and verify that execution stops.
    @routing_function
    def loop_router(state: State):
        return "loop"

    @node_action
    def loop_node(state: State):
        state.messages.append(1)
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("loop", loop_node))
    # Create a cycle: start -> loop and loop -> loop via conditional edge.
    builder.add_concrete_edge("start", "loop")
    builder.add_node(ProcessingNode("node2", passThrough))
    builder.add_conditional_edge("loop", ["loop"], loop_router)
    builder.add_concrete_edge("node2", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[])
    executor = GraphExecutor(graph, initial_state)
    with pytest.raises(GraphExecutionError):
        await executor.execute(max_supersteps=3)


def test_26_toolnode_missing_description():
    # Define a tool method with no docstring and an empty description.
    def tool_method(state: State) -> State:
        state.messages.append(42)
        return state

    # Ensure no docstring and no description provided.
    tool_method.__doc__ = None
    tool_method.is_tool_method = True
    with pytest.raises(EmptyToolNodeDescriptionError):
        # Attempt to create a ToolNode without a description.
        _ = ToolNode("tool", "", tool_method)


@pytest.mark.asyncio
async def test_27_successful_toolnode_execution():
    # Define a properly decorated tool method with a valid description.
    @tool_method
    def valid_tool(state: State) -> State:
        """A valid tool method that appends 999."""
        state.messages.append(999)
        return state

    builder = GraphBuilder()
    tool_node = ToolNode("tool", "Appends 999 to state", valid_tool)
    builder.add_node(tool_node)
    builder.add_concrete_edge("start", "tool")
    builder.add_concrete_edge("tool", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[])
    executor = GraphExecutor(graph, initial_state)
    final_state = await executor.execute()
    assert 999 in final_state.messages


@pytest.mark.asyncio
async def test_28_aggregator_invalid_output():
    # Aggregator action that returns a non-State value.
    @aggregator_action
    def bad_agg(states: List[State]):
        return 123  # Invalid output

    builder = GraphBuilder()
    # Add two simple processing nodes.
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_node(ProcessingNode("node2", passThrough))
    # Add an aggregator node with the bad aggregator action.
    builder.add_aggregator(AggregatorNode("agg", bad_agg))
    # Build a graph that sends states from node1 and node2 into the aggregator.
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("start", "node2")
    builder.add_concrete_edge("node1", "agg")
    builder.add_concrete_edge("node2", "agg")
    builder.add_concrete_edge("agg", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[10])
    executor = GraphExecutor(graph, initial_state)
    with pytest.raises((InvalidAggregatorActionError, GraphExecutionError)):
        await executor.execute()


@pytest.mark.asyncio
async def test_29_routing_function_invalid_output():
    @routing_function
    def bad_router(state: State):
        return 123  # Should be a string

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_concrete_edge("start", "node1")
    builder.add_conditional_edge("node1", ["end"], bad_router)
    graph = builder.build_graph()
    initial_state = State(messages=[])
    executor = GraphExecutor(graph, initial_state)
    # During execution, when node1 is processed, the bad_router will be invoked.
    with pytest.raises((InvalidRoutingFunctionOutput, GraphExecutionError)):
        await executor.execute()


@pytest.mark.asyncio
async def test_30_node_action_invalid_output():
    # Node action that returns a non-State value.
    @node_action
    def bad_node_action(state: State):
        return 123  # Invalid output

    builder = GraphBuilder()
    # This should raise an error upon execution because the node action returns non-State.
    builder.add_node(ProcessingNode("badnode", bad_node_action))
    builder.add_concrete_edge("start", "badnode")
    builder.add_concrete_edge("badnode", "end")
    graph = builder.build_graph()
    initial_state = State(messages=[5])
    executor = GraphExecutor(graph, initial_state)
    with pytest.raises((InvalidNodeActionOutput, GraphExecutionError)):
        await executor.execute()


def test_31_tool_method_not_decorated():
    # Define a tool method that is not decorated with the tool method marker.
    def not_decorated_tool(state: State) -> State:
        return state

    # Do not set the is_tool_method flag.
    with pytest.raises(ToolMethodNotDecorated):
        _ = ToolNode("tool", "Has no proper decoration", not_decorated_tool)


@pytest.mark.asyncio
async def test_32_node_execution_timeout():
    @node_action
    async def slow_node(state: State):
        await asyncio.sleep(2)
        state.messages.append(999)
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("slow", slow_node))
    builder.add_concrete_edge("start", "slow")
    builder.add_concrete_edge("slow", "end")
    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))

    with pytest.raises(GraphExecutionError) as exc_info:
        await executor.execute(superstep_timeout=1)

    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_33_aggregator_insufficient_states():
    @aggregator_action
    def strict_agg(states: List[State]):
        if len(states) != 2:
            raise ValueError("Expected exactly 2 states")
        return states[0]

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", passThrough))
    builder.add_aggregator(AggregatorNode("agg", strict_agg))
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("node1", "agg")
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    initial_state = State(messages=[0])
    executor = GraphExecutor(graph, initial_state)

    with pytest.raises(GraphExecutionError):
        await executor.execute()


@pytest.mark.asyncio
async def test_34_aggregator_state_isolation():
    @aggregator_action
    def isolating_agg(states: List[State]):
        states[0].messages.append("MODIFIED")
        return states[0]

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", passThrough))
    builder.add_node(ProcessingNode("n2", passThrough))
    builder.add_aggregator(AggregatorNode("agg", isolating_agg))
    builder.add_concrete_edge("start", "n1")
    builder.add_concrete_edge("start", "n2")
    builder.add_concrete_edge("n1", "agg")
    builder.add_concrete_edge("n2", "agg")
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    initial_state = State(messages=["A"])
    executor = GraphExecutor(graph, initial_state)
    final_state = await executor.execute()
    # Ensure only the output state is modified
    assert "MODIFIED" in final_state.messages


@pytest.mark.asyncio
async def test_35_routing_to_nonexistent_node():
    @routing_function
    def invalid_router(state: State):
        return "ghost"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", passThrough))
    builder.add_concrete_edge("start", "n1")
    builder.add_conditional_edge("n1", ["end"], invalid_router)

    graph = builder.build_graph()
    initial_state = State(messages=["hello"])
    executor = GraphExecutor(graph, initial_state)

    with pytest.raises(GraphExecutionError) as cm:
        await executor.execute()

    assert "ghost" in str(cm.value)


@pytest.mark.asyncio
async def test_36_empty_state_messages():
    @node_action
    def noop(state: State):
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("noop", noop))
    builder.add_concrete_edge("start", "noop")
    builder.add_concrete_edge("noop", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()

    assert final_state.messages == []


@pytest.mark.asyncio
async def test_37_mutated_shared_state():
    @node_action
    def mutate_state(state: State):
        state.messages.append("MUTATED")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", mutate_state))
    builder.add_node(ProcessingNode("n2", passThrough))
    builder.add_concrete_edge("start", "n1")
    builder.add_concrete_edge("start", "n2")
    builder.add_concrete_edge("n1", "end")
    builder.add_concrete_edge("n2", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=["A"]))
    final_state = await executor.execute()

    # Assert we only see one MUTATED, not duplication due to shared state mutation
    assert final_state.messages.count("MUTATED") <= 1


@pytest.mark.asyncio
async def test_38_toolnode_docstring_suffices():
    @tool_method
    def documented_tool(state: State):
        """This tool works without an explicit description."""
        state.messages.append("OK")
        return state

    tool_node = ToolNode("doc_tool", None, documented_tool)
    builder = GraphBuilder()
    builder.add_node(tool_node)
    builder.add_concrete_edge("start", "doc_tool")
    builder.add_concrete_edge("doc_tool", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()
    assert "OK" in final_state.messages


@pytest.mark.asyncio
async def test_39_single_input_to_aggregator():
    @aggregator_action
    def pass_through(states: List[State]):
        return states[0]

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("solo", passThrough))
    builder.add_aggregator(AggregatorNode("agg", pass_through))
    builder.add_concrete_edge("start", "solo")
    builder.add_concrete_edge("solo", "agg")
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=["solo"]))
    final_state = await executor.execute()
    assert "solo" in final_state.messages


@pytest.mark.asyncio
async def test_40_blank_routing_output():
    @routing_function
    def bad_router(state: State):
        return ""  # Invalid node ID

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", passThrough))
    builder.add_concrete_edge("start", "n1")
    builder.add_conditional_edge("n1", ["end"], bad_router)
    graph = builder.build_graph()

    executor = GraphExecutor(graph, State(messages=["blank"]))
    with pytest.raises(GraphExecutionError) as cm:
        await executor.execute()
    assert "''" in str(cm.value)  # check blank is part of error


@pytest.mark.asyncio
async def test_41_aggregator_state_post_mutation_check():
    # Aggregator will mutate after return just to test side effects
    captured = {}

    @aggregator_action
    def sneaky_agg(states: List[State]):
        s = states[0]
        result = State(messages=list(s.messages))
        captured["ref"] = result
        return result

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", passThrough))
    builder.add_node(ProcessingNode("n2", passThrough))
    builder.add_aggregator(AggregatorNode("agg", sneaky_agg))
    builder.add_concrete_edge("start", "n1")
    builder.add_concrete_edge("start", "n2")
    builder.add_concrete_edge("n1", "agg")
    builder.add_concrete_edge("n2", "agg")
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=["hi"]))
    final_state = await executor.execute()
    captured["ref"].messages.append("SNEAKY")  # post-mutation

    # Ensure original final_state is unaffected
    assert "SNEAKY" not in final_state.messages


@pytest.mark.asyncio
async def test_42_concurrent_aggregators_do_not_interfere():
    @node_action
    def node1(state: State):
        state.messages.append("A")
        return state

    @node_action
    def node2(state: State):
        state.messages.append("B")
        return state

    @aggregator_action
    def aggregate(states: List[State]):
        combined = []
        for s in states:
            combined.extend(s.messages)
        return State(messages=combined)

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", node1))
    builder.add_node(ProcessingNode("node2", node2))
    builder.add_aggregator(AggregatorNode("agg", aggregate))
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("start", "node2")
    builder.add_concrete_edge("node1", "agg")
    builder.add_concrete_edge("node2", "agg")
    builder.add_concrete_edge("agg", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    result = await executor.execute()
    assert sorted(result.messages) == ["A", "B"]


@pytest.mark.asyncio
async def test_43_async_toolnodes_parallel_execution():
    @tool_method
    async def async_tool(state: State):
        await asyncio.sleep(0.2)
        state.messages.append("tool")
        return state

    builder = GraphBuilder()
    builder.add_node(ToolNode("tool1", "Async Tool", async_tool))
    builder.add_node(ToolNode("tool2", "Async Tool", async_tool))
    builder.add_concrete_edge("start", "tool1")
    builder.add_concrete_edge("start", "tool2")
    builder.add_concrete_edge("tool1", "end")
    builder.add_concrete_edge("tool2", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    final_state = await executor.execute()
    assert final_state.messages.count("tool") <= 2


@pytest.mark.asyncio
async def test_44_heavy_parallel_graph():
    @tool_method
    async def heavy_tool(state: State) -> State:
        # Random delay simulating variable workload.
        await asyncio.sleep(random.uniform(0.01, 0.05))
        state.messages.append("heavy")
        return state

    @aggregator_action
    def combine_heavy(states: list[State]) -> State:
        combined = State(messages=[])
        for s in states:
            combined.messages.extend(s.messages)
        combined.messages.append("combined")
        return combined

    builder = GraphBuilder()
    # Create 20 parallel heavy_tool nodes.
    for i in range(20):
        node_id = f"node_{i}"
        builder.add_node(ToolNode(node_id, f"Heavy tool {i}", heavy_tool))
        builder.add_concrete_edge("start", node_id)
    # An aggregator to combine the outputs.
    builder.add_aggregator(AggregatorNode("agg_heavy", combine_heavy))
    for i in range(20):
        builder.add_concrete_edge(f"node_{i}", "agg_heavy")
    builder.add_concrete_edge("agg_heavy", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()

    # Expect 20 "heavy" messages and one "combined" marker.
    assert final_state.messages.count("heavy") == 20
    assert "combined" in final_state.messages


@pytest.mark.asyncio
async def test_45_graph_with_only_toolnodes():
    @tool_method
    def tool_step(state: State):
        state.messages.append("step")
        return state

    builder = GraphBuilder()
    builder.add_node(ToolNode("tool1", "1st Tool", tool_step))
    builder.add_node(ToolNode("tool2", "2nd Tool", tool_step))
    builder.add_concrete_edge("start", "tool1")
    builder.add_concrete_edge("tool1", "tool2")
    builder.add_concrete_edge("tool2", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    final_state = await executor.execute()
    assert final_state.messages == ["step", "step"]


@pytest.mark.asyncio
async def test_46_ai_action_integration():
    class DummyAIAction(AIActionBase):
        def build_model(self):
            self.model = "dummy"
            self._model_built = True

        async def process_state(self, state: State):
            state.messages.append("ai")
            return state

    ai_node = AINode("ai", "dummy ai", DummyAIAction({}))
    builder = GraphBuilder()
    builder.add_node(ai_node)
    builder.add_concrete_edge("start", "ai")
    builder.add_concrete_edge("ai", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    result = await executor.execute()
    assert "ai" in result.messages


@pytest.mark.asyncio
async def test_47_processing_node_sync():
    @node_action
    def sync_action(state):
        state.messages.append("sync")
        return state

    node = ProcessingNode("proc", sync_action)
    result = await node.execute(State(messages=[]))
    assert result.messages == ["sync"]


@pytest.mark.asyncio
async def test_48_processing_node_async():
    @node_action
    async def async_action(state):
        await asyncio.sleep(0.01)
        state.messages.append("async")
        return state

    node = ProcessingNode("proc", async_action)
    result = await node.execute(State(messages=[]))
    assert result.messages == ["async"]


@pytest.mark.asyncio
async def test_49_tool_node_async():
    @tool_method
    async def tool(state):
        await asyncio.sleep(0.01)
        state.messages.append("tool")
        return state

    node = ToolNode("tool", "description", tool)
    result = await node.execute(State(messages=[]))
    assert result.messages == ["tool"]


@pytest.mark.asyncio
async def test_50_ai_node_executes():
    class DummyAIAction(AIActionBase):
        def build_model(self):
            self._model_built = True

        async def process_state(self, state):
            state.messages.append("ai")
            return state

    ai_node = AINode("ai", "desc", DummyAIAction({}))
    result = await ai_node.execute(State(messages=[]))
    assert "ai" in result.messages


@pytest.mark.asyncio
async def test_51_aggregator_node_sync():
    @aggregator_action
    def aggregator(states):
        s = states[0]
        s.messages.append("agg")
        return s

    node = AggregatorNode("agg", aggregator)
    result = await node.execute([State(messages=["a"]), State(messages=["b"])])
    assert "agg" in result.messages


@pytest.mark.asyncio
async def test_52_aggregator_node_async():
    @aggregator_action
    async def aggregator(states):
        await asyncio.sleep(0.01)
        s = states[0]
        s.messages.append("agg")
        return s

    node = AggregatorNode("agg", aggregator)
    result = await node.execute([State(messages=["1"]), State(messages=["2"])])
    assert "agg" in result.messages


@pytest.mark.asyncio
async def test_53_async_routing_function():
    @routing_function
    async def router(state):
        await asyncio.sleep(0.01)
        return "end"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", passThrough))
    builder.add_concrete_edge("start", "n1")
    builder.add_conditional_edge("n1", ["end"], router)
    executor = GraphExecutor(builder.build_graph(), State(messages=["r"]))
    result = await executor.execute()
    assert result is not None


@pytest.mark.asyncio
async def test_54_graph_mixed_nodes():
    @node_action
    def p1(state):
        state.messages.append("p1")
        return state

    @tool_method
    async def t1(state):
        state.messages.append("t1")
        return state

    @node_action
    def p2(state):
        state.messages.append("p2")
        return state

    @aggregator_action
    async def agg(states: List[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        merged.messages.append("agg")
        return merged

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("p1", p1))
    builder.add_node(ToolNode("t1", "desc", t1))
    builder.add_node(ProcessingNode("p2", p2))
    builder.add_aggregator(AggregatorNode("agg", agg))

    builder.add_concrete_edge("start", "p1")
    builder.add_concrete_edge("start", "t1")
    builder.add_concrete_edge("p1", "agg")
    builder.add_concrete_edge("t1", "agg")
    builder.add_concrete_edge("agg", "p2")
    builder.add_concrete_edge("p2", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    result = await executor.execute()
    for label in {"p1", "t1", "agg", "p2"}:
        assert (
            label in result.messages
        ), f"{label} not found in state: {result.messages}"


@pytest.mark.asyncio
async def test_55_aggregator_single_input_still_works():
    @aggregator_action
    def agg(states):
        return states[0]

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("solo", passThrough))
    builder.add_aggregator(AggregatorNode("agg", agg))
    builder.add_concrete_edge("start", "solo")
    builder.add_concrete_edge("solo", "agg")
    builder.add_concrete_edge("agg", "end")
    result = await GraphExecutor(
        builder.build_graph(), State(messages=["ok"])
    ).execute()
    assert "ok" in result.messages


@pytest.mark.asyncio
async def test_56_retry_logic_on_tool_node():
    count = {"tries": 0}

    @tool_method
    async def flaky_tool(state):
        if count["tries"] < 1:
            count["tries"] += 1
            raise ValueError("fail once")
        state.messages.append("recovered")
        return state

    builder = GraphBuilder()
    builder.add_node(ToolNode("flaky", "unstable", flaky_tool))
    builder.add_concrete_edge("start", "flaky")
    builder.add_concrete_edge("flaky", "end")
    result = await GraphExecutor(
        builder.build_graph(), State(messages=[]), retry_policy=RetryPolicy()
    ).execute()
    assert "recovered" in result.messages


@pytest.mark.asyncio
async def test_57_parallel_nodes_with_aggregator():
    @tool_method
    async def async_tool1(state: State) -> State:
        await asyncio.sleep(0.1)
        state.messages.append("async_tool1")
        return state

    @tool_method
    async def async_tool2(state: State) -> State:
        await asyncio.sleep(0.05)
        state.messages.append("async_tool2")
        return state

    @aggregator_action
    def merge_agg(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        merged.messages.append("aggregated")
        return merged

    builder = GraphBuilder()
    builder.add_node(ToolNode("t1", "Async tool 1", async_tool1))
    builder.add_node(ToolNode("t2", "Async tool 2", async_tool2))
    builder.add_aggregator(AggregatorNode("agg", merge_agg))
    builder.add_concrete_edge("start", "t1")
    builder.add_concrete_edge("start", "t2")
    builder.add_concrete_edge("t1", "agg")
    builder.add_concrete_edge("t2", "agg")
    builder.add_concrete_edge("agg", "end")
    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()
    assert "async_tool1" in final_state.messages
    assert "async_tool2" in final_state.messages
    assert "aggregated" in final_state.messages


@pytest.mark.asyncio
async def test_58_sync_ai_action_works():
    # Here we intentionally define process_state as a synchronous method.
    class DummySyncAIAction(AIActionBase):
        def build_model(self):
            self.model = "dummy"
            self._model_built = True

        def process_state(self, state: State) -> State:
            state.messages.append("ai_sync")
            return state

    ai_node = AINode("ai_sync", "Sync AI", DummySyncAIAction({}))
    builder = GraphBuilder()
    builder.add_node(ai_node)
    builder.add_concrete_edge("start", "ai_sync")
    builder.add_concrete_edge("ai_sync", "end")
    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()
    assert "ai_sync" in final_state.messages


@pytest.mark.asyncio
async def test_59_async_ai_action_works():
    class DummyAsyncAIAction(AIActionBase):
        def build_model(self):
            self.model = "dummy"
            self._model_built = True

        async def process_state(self, state: State) -> State:
            state.messages.append("ai_async")
            return state

    ai_node = AINode("ai_async", "Async AI", DummyAsyncAIAction({}))
    builder = GraphBuilder()
    builder.add_node(ai_node)
    builder.add_concrete_edge("start", "ai_async")
    builder.add_concrete_edge("ai_async", "end")
    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()
    assert "ai_async" in final_state.messages


@pytest.mark.asyncio
async def test_60_aggregator_state_independence():
    @node_action
    def node1(state: State) -> State:
        state.messages.append("node1")
        return state

    @node_action
    def node2(state: State) -> State:
        state.messages.append("node2")
        return state

    @aggregator_action
    def merge_states(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        merged.messages.append("merged")
        return merged

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", node1))
    builder.add_node(ProcessingNode("n2", node2))
    builder.add_aggregator(AggregatorNode("agg", merge_states))
    builder.add_concrete_edge("start", "n1")
    builder.add_concrete_edge("start", "n2")
    builder.add_concrete_edge("n1", "agg")
    builder.add_concrete_edge("n2", "agg")
    builder.add_concrete_edge("agg", "end")
    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()
    # Expect that both node messages appear and then the aggregator adds "merged".
    assert "node1" in final_state.messages
    assert "node2" in final_state.messages
    assert "merged" in final_state.messages


@pytest.mark.asyncio
async def test_61_robust_parallel_random_delays():
    # Create several async nodes with random delays.
    @tool_method
    async def delayed_tool(state: State) -> State:
        delay = random.uniform(0.01, 0.1)
        await asyncio.sleep(delay)
        state.messages.append(f"delayed_{delay:.2f}")
        return state

    @aggregator_action
    def merge_messages(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        merged.messages.append("merged")
        return merged

    builder = GraphBuilder()
    # Add 5 parallel delayed nodes.
    for i in range(5):
        builder.add_node(ToolNode(f"tool{i}", f"delayed tool {i}", delayed_tool))
        builder.add_concrete_edge("start", f"tool{i}")
    # Aggregator node to merge outputs.
    builder.add_aggregator(AggregatorNode("agg", merge_messages))
    for i in range(5):
        builder.add_concrete_edge(f"tool{i}", "agg")
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()

    # Check that messages from all nodes and the aggregator are present.
    for i in range(5):
        assert any(f"delayed_" in msg for msg in final_state.messages)
    assert "merged" in final_state.messages


@pytest.mark.asyncio
async def test_62_state_deepcopy_isolation():
    @node_action
    def node_a(state: State) -> State:
        state.messages.append("A")
        return state

    @node_action
    def node_b(state: State) -> State:
        state.messages.append("B")
        # Further mutate state after returning.
        state.messages.append("B_extra")
        return state

    @aggregator_action
    def aggregate_states(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        return merged

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("a", node_a))
    builder.add_node(ProcessingNode("b", node_b))
    builder.add_aggregator(AggregatorNode("agg", aggregate_states))
    builder.add_concrete_edge("start", "a")
    builder.add_concrete_edge("start", "b")
    builder.add_concrete_edge("a", "agg")
    builder.add_concrete_edge("b", "agg")
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=["start"]))
    final_state = await executor.execute()

    # Verify that both "A" and "B" (plus "B_extra") appear.
    assert "A" in final_state.messages
    assert "B" in final_state.messages
    assert "B_extra" in final_state.messages


@pytest.mark.asyncio
async def test_63_error_propagation_in_node():
    @node_action
    def faulty_node(state: State) -> State:
        raise ValueError("Deliberate failure")

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("faulty", faulty_node))
    builder.add_concrete_edge("start", "faulty")
    builder.add_concrete_edge("faulty", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))

    with pytest.raises(GraphExecutionError) as exc_info:
        await executor.execute()
    assert "Deliberate failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_64_retry_policy_custom():
    call_count = {"tries": 0}

    @node_action
    def flaky_node(state: State) -> State:
        call_count["tries"] += 1
        if call_count["tries"] < 3:
            raise Exception("Temporary failure")
        state.messages.append("success")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("flaky", flaky_node))
    builder.add_concrete_edge("start", "flaky")
    builder.add_concrete_edge("flaky", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(
        graph,
        State(messages=[]),
        retry_policy=RetryPolicy(max_retries=5, delay=0.1, backoff=1),
    )
    final_state = await executor.execute()
    assert "success" in final_state.messages
    assert call_count["tries"] == 3


@pytest.mark.asyncio
async def test_65_async_conditional_routing():
    @node_action
    def start_node(state: State) -> State:
        state.messages.append("start")
        return state

    @routing_function
    async def async_router(state: State) -> str:
        # Simulate asynchronous decision-making with a delay.
        await asyncio.sleep(0.05)
        if "start" in state.messages:
            return "branch1"
        return "branch2"

    @node_action
    def branch1(state: State) -> State:
        state.messages.append("branch1")
        return state

    @node_action
    def branch2(state: State) -> State:
        state.messages.append("branch2")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("start_node", start_node))
    builder.add_node(ProcessingNode("branch1", branch1))
    builder.add_node(ProcessingNode("branch2", branch2))
    builder.add_concrete_edge("start", "start_node")
    builder.add_conditional_edge("start_node", ["branch1", "branch2"], async_router)
    builder.add_concrete_edge("branch1", "end")
    builder.add_concrete_edge("branch2", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()
    # Check that one of the branches was taken.
    assert "branch1" in final_state.messages or "branch2" in final_state.messages


@pytest.mark.asyncio
async def test_66_mixed_sync_async_toolnodes():
    @tool_method
    def sync_tool(state: State) -> State:
        state.messages.append("sync_tool")
        return state

    @tool_method
    async def async_tool(state: State) -> State:
        await asyncio.sleep(0.02)
        state.messages.append("async_tool")
        return state

    @aggregator_action
    def merge_tools(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        return merged

    builder = GraphBuilder()
    builder.add_node(ToolNode("sync", "Sync Tool", sync_tool))
    builder.add_node(ToolNode("async", "Async Tool", async_tool))
    builder.add_aggregator(AggregatorNode("agg", merge_tools))
    builder.add_concrete_edge("start", "sync")
    builder.add_concrete_edge("start", "async")
    builder.add_concrete_edge("sync", "agg")
    builder.add_concrete_edge("async", "agg")
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    final_state = await executor.execute()
    assert "sync_tool" in final_state.messages
    assert "async_tool" in final_state.messages


@pytest.mark.asyncio
async def test_67_nested_state_structure():
    @node_action
    def nested_node(state: State) -> State:
        # Append a nested dict.
        state.messages.append({"val": 1})
        return state

    @aggregator_action
    def merge_nested(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        return merged

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("nested", nested_node))
    builder.add_aggregator(AggregatorNode("agg_nested", merge_nested))
    builder.add_concrete_edge("start", "nested")
    builder.add_concrete_edge("nested", "agg_nested")
    builder.add_concrete_edge("agg_nested", "end")

    initial_state = State(messages=[{"base": True}])
    executor = GraphExecutor(builder.build_graph(), initial_state)
    final_state = await executor.execute()

    # Mutate the nested dicts in the final state.
    for msg in final_state.messages:
        if isinstance(msg, dict) and "val" in msg:
            msg["val"] += 100
    # Confirm that the initial state's nested dict remains unchanged.
    assert initial_state.messages[0]["base"] is True


@pytest.mark.asyncio
async def test_68_multiple_conditional_edges():
    @node_action
    def cond_node(state: State) -> State:
        state.messages.append("cond")
        return state

    @routing_function
    async def multi_router(state: State) -> str:
        await asyncio.sleep(0.02)
        # Randomly select one of three branches.
        return random.choice(["branch1", "branch2", "branch3"])

    @node_action
    def branch1(state: State) -> State:
        state.messages.append("branch1")
        return state

    @node_action
    def branch2(state: State) -> State:
        state.messages.append("branch2")
        return state

    @node_action
    def branch3(state: State) -> State:
        state.messages.append("branch3")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("cond_node", cond_node))
    builder.add_node(ProcessingNode("branch1", branch1))
    builder.add_node(ProcessingNode("branch2", branch2))
    builder.add_node(ProcessingNode("branch3", branch3))
    builder.add_concrete_edge("start", "cond_node")
    builder.add_conditional_edge(
        "cond_node", ["branch1", "branch2", "branch3"], multi_router
    )
    builder.add_concrete_edge("branch1", "end")
    builder.add_concrete_edge("branch2", "end")
    builder.add_concrete_edge("branch3", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    final_state = await executor.execute()
    # Verify that at least one branch message is present.
    branches = {"branch1", "branch2", "branch3"}
    assert any(b in final_state.messages for b in branches)


@pytest.mark.asyncio
async def test_69_execution_exceeds_max_supersteps():
    @node_action
    def looping_node(state: State) -> State:
        state.messages.append("loop")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("loop", looping_node))
    # Loop: start -> loop and then loop -> loop via a conditional edge.
    builder.add_concrete_edge("start", "loop")

    @routing_function
    def loop_router(state: State) -> str:
        return "loop"

    builder.add_conditional_edge("loop", ["loop"], loop_router)
    builder.add_concrete_edge("loop", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    with pytest.raises(GraphExecutionError) as exc_info:
        await executor.execute(max_supersteps=3)
    # Check that an error about supersteps or looping is raised.
    assert "Max supersteps reached" in str(exc_info.value) or "loop" in str(
        exc_info.value
    )


@pytest.mark.asyncio
async def test_70_invalid_conditional_routing():
    @node_action
    def base_node(state: State) -> State:
        state.messages.append("base")
        return state

    @routing_function
    async def invalid_router(state: State) -> str:
        return "nonexistent"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("base", base_node))
    builder.add_concrete_edge("start", "base")
    builder.add_conditional_edge("base", ["end"], invalid_router)
    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    with pytest.raises(GraphExecutionError) as exc_info:
        await executor.execute()
    assert "nonexistent" in str(exc_info.value)


@pytest.mark.asyncio
async def test_71_mixed_complex_graph():
    # A graph mixing processing, tool, aggregator, and conditional nodes.
    @node_action
    def proc1(state: State) -> State:
        state.messages.append("proc1")
        return state

    @tool_method
    async def tool1(state: State) -> State:
        await asyncio.sleep(0.03)
        state.messages.append("tool1")
        return state

    @aggregator_action
    def agg1(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        merged.messages.append("agg1")
        return merged

    @routing_function
    async def complex_router(state: State) -> str:
        await asyncio.sleep(0.01)
        # If "proc1" is present, route to the tool branch; otherwise, to aggregator branch.
        return "tool_branch" if "proc1" in state.messages else "agg_branch"

    @node_action
    def proc2(state: State) -> State:
        state.messages.append("proc2")
        return state

    @node_action
    def tool_branch(state: State) -> State:
        state.messages.append("branch_tool")
        return state

    @node_action
    def agg_branch(state: State) -> State:
        state.messages.append("branch_agg")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("proc1", proc1))
    builder.add_node(ToolNode("tool1", "Tool Node 1", tool1))
    builder.add_node(ProcessingNode("proc2", proc2))
    builder.add_aggregator(AggregatorNode("agg1", agg1))
    # Add branch nodes before adding the conditional edge.
    builder.add_node(ProcessingNode("tool_branch", tool_branch))
    builder.add_node(ProcessingNode("agg_branch", agg_branch))
    # Now add edges.
    builder.add_concrete_edge("start", "proc1")
    builder.add_conditional_edge("proc1", ["tool_branch", "agg_branch"], complex_router)
    builder.add_concrete_edge("tool_branch", "agg1")
    builder.add_concrete_edge("agg_branch", "agg1")
    builder.add_concrete_edge("agg1", "proc2")
    builder.add_concrete_edge("proc2", "end")

    executor = GraphExecutor(builder.build_graph(), State(messages=[]))
    final_state = await executor.execute()

    # Expected messages: "proc1", one branch message ("branch_tool" or "branch_agg"), "agg1", and "proc2".
    expected = {"proc1", "agg1", "proc2"}
    for item in expected:
        assert (
            item in final_state.messages
        ), f"{item} not found in {final_state.messages}"
    assert "branch_tool" in final_state.messages or "branch_agg" in final_state.messages


@pytest.mark.asyncio
async def test_72_concurrency_limit():
    # Local counters to track concurrency.
    counters = {"current": 0, "max": 0}

    @node_action
    async def delayed_node(state: State) -> State:
        counters["current"] += 1
        counters["max"] = max(counters["max"], counters["current"])
        # Simulate work with a delay.
        await asyncio.sleep(0.2)
        counters["current"] -= 1
        state.messages.append("done")
        return state

    @aggregator_action
    def merge_states(states: list[State]) -> State:
        merged = State(messages=[])
        for s in states:
            merged.messages.extend(s.messages)
        return merged

    builder = GraphBuilder()
    # Add the aggregator node first so it exists when processing nodes connect to it.
    builder.add_aggregator(AggregatorNode("agg", merge_states))

    # Create 5 processing nodes.
    for i in range(5):
        node_id = f"node_{i}"
        builder.add_node(ProcessingNode(node_id, delayed_node))
        builder.add_concrete_edge("start", node_id)
        builder.add_concrete_edge(node_id, "agg")

    # Connect aggregator node to the "end" node.
    builder.add_concrete_edge("agg", "end")

    graph = builder.build_graph()
    # Set max_workers to 2 so that at most 2 nodes run concurrently.
    executor = GraphExecutor(graph, State(messages=[]), max_workers=2)
    final_state = await executor.execute()

    # Verify that all 5 processing nodes appended "done".
    assert final_state.messages.count("done") == 5
    # Ensure that the maximum concurrent executions did not exceed 2.
    assert counters["max"] <= 2


@pytest.mark.asyncio
async def test_73_human_node_sync_success():
    @node_action
    def sync_handler(state: State) -> State:
        state.messages.append("approved")
        return state

    node = HumanInTheLoopNode("hitl_sync", sync_handler)
    result = await node.execute(State(messages=["start"]))
    assert "approved" in result.messages


@pytest.mark.asyncio
async def test_74_human_node_async_success():
    @node_action
    async def async_handler(state: State) -> State:
        await asyncio.sleep(0.01)
        state.messages.append("async approved")
        return state

    node = HumanInTheLoopNode("hitl_async", async_handler)
    result = await node.execute(State(messages=["go"]))
    assert "async approved" in result.messages


@pytest.mark.asyncio
async def test_75_human_node_retries_exhausted():
    @node_action
    async def always_fail(state: State) -> State:
        raise Exception("Nope")

    node = HumanInTheLoopNode("hitl_fail", always_fail)

    with pytest.raises(Exception) as excinfo:
        await node.execute(State(messages=[]))

    assert "Nope" in str(excinfo.value)


@pytest.mark.asyncio
async def test_77_human_node_invalid_return_type():
    @node_action
    async def bad_handler(state: State):
        return "not a state"

    node = HumanInTheLoopNode("bad_node", bad_handler)

    with pytest.raises(InvalidNodeActionOutput) as excinfo:
        await node.execute(State(messages=["X"]))

    assert "not a state" in str(excinfo.value)


@pytest.mark.asyncio
async def test_78_fallback_node_executes_on_failure():
    call_log = []

    @node_action
    def fail_node(state: State) -> State:
        call_log.append("main")
        raise ValueError("Failure")

    @node_action
    def fallback_node(state: State) -> State:
        call_log.append("fallback")
        state.messages.append("Recovered")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("main", fail_node))
    builder.add_node(ProcessingNode("fallback", fallback_node))
    builder.set_fallback_node("main", "fallback")
    builder.add_concrete_edge("start", "main")
    builder.add_concrete_edge("main", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]), retry_policy=RetryPolicy())
    result = await executor.execute()
    assert "Recovered" in result.messages
    assert call_log.count("main") == 4  # 1 + 3 retries
    assert call_log[-1] == "fallback"  # Last call should be fallback


@pytest.mark.asyncio
async def test_79_no_fallback_failure_raises_error():
    @node_action
    def fail_node(state: State) -> State:
        raise RuntimeError("Intentional")

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("main", fail_node))
    builder.add_concrete_edge("start", "main")
    builder.add_concrete_edge("main", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    with pytest.raises(GraphExecutionError) as excinfo:
        await executor.execute()
    assert "Intentional" in str(excinfo.value)


@pytest.mark.asyncio
async def test_80_fallback_failure_raises_proper_error():
    @node_action
    def fail_node(state: State) -> State:
        raise RuntimeError("Primary failed")

    @node_action
    def fallback_node(state: State) -> State:
        raise RuntimeError("Fallback also failed")

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("main", fail_node))
    builder.add_node(ProcessingNode("fallback", fallback_node))
    builder.set_fallback_node("main", "fallback")
    builder.add_concrete_edge("start", "main")
    builder.add_concrete_edge("main", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    with pytest.raises(GraphExecutionError) as excinfo:
        await executor.execute()
    assert "Fallback also failed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_81_fallback_conditional_edge_routing():
    @node_action
    def fail_node(state: State) -> State:
        raise ValueError("Failing deliberately")

    @node_action
    def fallback_node(state: State) -> State:
        state.messages.append("Fallback used")
        return state

    @node_action
    def sink_node(state: State) -> State:
        state.messages.append("Sink reached")
        return state

    @routing_function
    def router(state: State) -> str:
        return "sink"

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("main", fail_node))
    builder.add_node(ProcessingNode("fallback", fallback_node))
    builder.add_node(ProcessingNode("sink", sink_node))

    builder.set_fallback_node("main", "fallback")
    builder.add_concrete_edge("start", "main")
    builder.add_conditional_edge("main", ["sink"], router)
    builder.add_concrete_edge("sink", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))
    result = await executor.execute()
    assert "Fallback used" in result.messages
    assert "Sink reached" in result.messages


@pytest.mark.asyncio
async def test_82_circle_graph_with_fallback():
    counter = {"value": 0}
    op = {"node1": 0, "node2": 0, "fall_node": 0}

    @node_action
    def flaky_node(state: State):
        op["node1"] += 1
        if counter["value"] == 0:
            counter["value"] += 1
            raise ValueError("Failing")
        else:
            return state

    @node_action
    def normal_node(state: State):
        op["node2"] += 1
        return state

    @node_action
    def fallback_node(state: State):
        op["fall_node"] += 1
        return state

    @routing_function
    def router(state: State) -> str:
        if counter["value"] == 1:
            counter["value"] += 1
            return "node1"
        else:
            return "end"

    node1 = ProcessingNode("node1", flaky_node)
    node2 = ProcessingNode("node2", normal_node)
    fall_node = ProcessingNode("fall_node", fallback_node)

    builder = GraphBuilder()
    builder.add_node(node1)
    builder.add_node(node2)
    builder.add_node(fall_node)
    builder.set_fallback_node("node1", "fall_node")
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("node1", "node2")
    builder.add_conditional_edge("node2", ["node1", "end"], router)

    graph = builder.build_graph()
    initial_state = State(messages=[])
    rp = RetryPolicy(0, 0, 0)
    executor = GraphExecutor(graph, initial_state, retry_policy=rp)
    result = await executor.execute()

    assert op["node1"] == 2
    assert op["node2"] == 2
    assert op["fall_node"] == 1


@pytest.mark.asyncio
async def test_83_node_with_custom_retry_policy_succeeds():
    call_count = {"tries": 0}

    @node_action
    async def flaky_action(state: State) -> State:
        call_count["tries"] += 1
        if call_count["tries"] < 3:
            raise Exception("Flaky failure")
        state.messages.append("Success")
        return state

    builder = GraphBuilder()
    flaky_node = ProcessingNode("flaky", flaky_action)
    builder.add_node(flaky_node)
    builder.add_concrete_edge("start", "flaky")
    builder.add_concrete_edge("flaky", "end")

    # Set custom retry policy
    builder.set_node_retry_policy(
        "flaky", RetryPolicy(max_retries=5, delay=0.01, backoff=1.0)
    )

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))

    final_state = await executor.execute()

    assert "Success" in final_state.messages
    assert call_count["tries"] == 3  # 2 failures + 1 success


@pytest.mark.asyncio
async def test_84_node_fallbacks_to_graph_retry_policy():
    call_count = {"tries": 0}

    @node_action
    async def flaky_action(state: State) -> State:
        call_count["tries"] += 1
        if call_count["tries"] < 2:
            raise Exception("Temporary failure")
        state.messages.append("Recovered")
        return state

    builder = GraphBuilder()
    flaky_node = ProcessingNode("flaky", flaky_action)
    builder.add_node(flaky_node)
    builder.add_concrete_edge("start", "flaky")
    builder.add_concrete_edge("flaky", "end")

    graph = builder.build_graph()

    # No node-level retry_policy set
    executor = GraphExecutor(
        graph,
        State(messages=[]),
        retry_policy=RetryPolicy(max_retries=3, delay=0.01, backoff=1.0),
    )

    final_state = await executor.execute()

    assert "Recovered" in final_state.messages
    assert call_count["tries"] == 2  # 1 failure + 1 success


@pytest.mark.asyncio
async def test_85_node_exceeds_retries_and_fails():
    call_count = {"tries": 0}

    @node_action
    async def always_fail(state: State) -> State:
        call_count["tries"] += 1
        raise Exception("Always failing")

    builder = GraphBuilder()
    fail_node = ProcessingNode("fail", always_fail)
    builder.add_node(fail_node)
    builder.add_concrete_edge("start", "fail")
    builder.add_concrete_edge("fail", "end")

    # Setting node retry policy to 2 retries
    builder.set_node_retry_policy(
        "fail", RetryPolicy(max_retries=2, delay=0.01, backoff=1.0)
    )

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=[]))

    with pytest.raises(GraphExecutionError) as exc_info:
        await executor.execute()

    assert "Always failing" in str(exc_info.value)
    assert call_count["tries"] == 3  # 1 initial + 2 retries

import time
import unittest
import matplotlib
# Use a non-interactive backend for testing so no window pops up.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import List
from graphorchestrator.GraphExecutorStatic import (
    State,
    DuplicateNodeError,
    NodeNotFoundError,
    EdgeExistsError,
    NodeActionNotDecoratedError,
    RoutingFunctionNotDecoratedError,
    ToolMethodNotDecorated,
    InvalideNodeActionOutput,
    InvalidAggregatorActionError,
    InvalidRoutingFunctionOutput,
    GraphConfigurationError,
    EmptyToolNodeDescriptionError,
    GraphExecutionError,
    ProcessingNode,
    AggregatorNode,
    ToolNode,
    ConditionalEdge,
    RetryPolicy,
    GraphBuilder,
    GraphExecutor,
    RepresentationalGraph,
    GraphVisualizer,
    passThrough,
    selectRandomState,
    node_action,
    aggregator_action,
    routing_function,
    tool_method
)

class GraphTests(unittest.TestCase):
    def setUp(self):
        print(f"\n\n🟡 STARTING: {self._testMethodName}")

    def tearDown(self):
        print(f"✅ FINISHED: {self._testMethodName}")    

    def test_01_valid_node_action_decorator(self):
        @node_action
        def valid_func(state):
            return state
        node = ProcessingNode("valid", valid_func)
        self.assertEqual(node.node_id, "valid")

    def test_02_missing_node_action_decorator(self):
        def bad_func(state):
            return state
        with self.assertRaises(NodeActionNotDecoratedError):
            ProcessingNode("invalid", bad_func)

    def test_03_missing_routing_decorator(self):
        def router(state):
            return "node3"
        node1 = ProcessingNode("node1", passThrough)
        node2 = ProcessingNode("node2", passThrough)
        node3 = ProcessingNode("node3", passThrough)
        with self.assertRaises(RoutingFunctionNotDecoratedError):
            ConditionalEdge(node1, [node2, node3], router)

    def test_04_duplicate_node_error(self):
        builder = GraphBuilder()
        node1 = ProcessingNode("node1", passThrough)
        builder.add_node(node1)
        with self.assertRaises(DuplicateNodeError):
            builder.add_node(ProcessingNode("node1", passThrough))

    def test_05_add_non_existing_node_on_concrete_edge(self):
        builder = GraphBuilder()
        node1 = ProcessingNode("node1", passThrough)
        builder.add_node(node1)
        with self.assertRaises(NodeNotFoundError):
            builder.add_concrete_edge("node1", "node2")

    def test_06_add_non_existing_node_on_conditional_edge(self):
        @routing_function
        def router(state):
            return "end"
        builder = GraphBuilder()
        node1 = ProcessingNode("node1", passThrough)
        builder.add_node(node1)
        with self.assertRaises(NodeNotFoundError):
            builder.add_conditional_edge("node1", ["node2", "end", "start"], router)

    def test_07_add_concrete_edge_on_concrete_edge(self):
        builder = GraphBuilder()
        node1 = ProcessingNode("node1", passThrough)
        node2 = ProcessingNode("node2", passThrough)
        builder.add_node(node1)
        builder.add_node(node2)
        builder.add_concrete_edge("node1", "node2")
        with self.assertRaises(EdgeExistsError):
            builder.add_concrete_edge("node1", "node2")

    def test_08_add_conditional_edge_on_concrete_edge(self):
        @routing_function
        def router(state):
            return "end"
        builder = GraphBuilder()
        node1 = ProcessingNode("node1", passThrough)
        node2 = ProcessingNode("node2", passThrough)
        builder.add_node(node1)
        builder.add_node(node2)
        builder.add_concrete_edge("node1", "node2")
        with self.assertRaises(EdgeExistsError):
            builder.add_conditional_edge("node1", ["node2", "end"], router)

    def test_09_add_concrete_edge_on_conditional_edge(self):
        @routing_function
        def router(state):
            return "end"
        builder = GraphBuilder()
        node1 = ProcessingNode("node1", passThrough)
        node2 = ProcessingNode("node2", passThrough)
        builder.add_node(node1)
        builder.add_node(node2)
        builder.add_conditional_edge("node1", ["node2", "end"], router)
        with self.assertRaises(EdgeExistsError):
            builder.add_concrete_edge("node1", "node2")
    
    def test_10_add_conditional_edge_on_conditional_edge(self):
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
        with self.assertRaises(EdgeExistsError):
            builder.add_conditional_edge("node1", ["node2", "node1"], router2)

    def test_11_graph_config_incoming_concrete_edge_to_start(self):
        builder = GraphBuilder()
        builder.add_node(ProcessingNode("node1", passThrough))
        with self.assertRaises(GraphConfigurationError):
            builder.add_concrete_edge("node1", "start")

    def test_12_graph_config_incoming_conditional_edge_to_start(self):
        @routing_function
        def router(state):
            return "start"
        builder = GraphBuilder()
        builder.add_node(ProcessingNode("node1", passThrough))
        with self.assertRaises(GraphConfigurationError):
            builder.add_conditional_edge("node1", ["node1", "start"], router)

    def test_13_graph_config_no_edge_from_start(self):
        builder = GraphBuilder()
        builder.add_node(ProcessingNode("node1", passThrough))
        builder.add_concrete_edge("node1", "end")
        with self.assertRaises(GraphConfigurationError):
            builder.build_graph()

    def test_14_graph_config_conditonal_edge_from_start(self):
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
        with self.assertRaises(GraphConfigurationError):
            builder.build_graph()

    def test_15_graph_config_no_outgoing_concrete_edge_from_end(self):
        builder = GraphBuilder()
        builder.add_node(ProcessingNode("node1", passThrough))
        builder.add_concrete_edge("start", "end")
        with self.assertRaises(GraphConfigurationError):
            builder.add_concrete_edge("end", "node1")

    def test_16_graph_config_no_outgoing_conditional_edge_from_end(self):
        @routing_function
        def router(state):
            return "node2"
        builder = GraphBuilder()
        builder.add_node(ProcessingNode("node1", passThrough))
        builder.add_node(ProcessingNode("node2", passThrough))
        builder.add_concrete_edge("start", "end")
        with self.assertRaises(GraphConfigurationError):
            builder.add_conditional_edge("end", ["node1", "node2"], router)

    def test_17_graph_config_no_edge_to_end(self):
        builder = GraphBuilder()
        builder.add_node(ProcessingNode("node1", passThrough))
        builder.add_concrete_edge("start", "node1")
        with self.assertRaises(GraphConfigurationError):
            builder.build_graph()
    
    def test_18_graph_config_conditional_edge_to_end(self):
        @routing_function
        def router(state):
            return "node1"
        builder = GraphBuilder()
        builder.add_node(ProcessingNode("node1", passThrough))
        builder.add_concrete_edge("start", "node1")
        builder.add_conditional_edge("node1", ["node1", "end"], router)

    def test_19_linear_graph(self):
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
        final_state = executor.execute()
        self.assertEqual(final_state, State(messages=[1, 2]))

    def test_20_single_node_looping(self):
        builder = GraphBuilder()
        @routing_function
        def router(state: State):
            latest_state = state.messages[-1]
            if latest_state%10 == 0:
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
        final_state = executor.execute()
        self.assertEqual(final_state, State(messages=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))

    def test_21_two_node_linear(self):
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
            latest_state = latest_state%2
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
        final_state = exeuctor.execute()
        self.assertEqual(final_state, State(messages=[11, 12, 0]))

    def test_22_graph_with_aggregator(self):
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
        final_state = executor.execute()
        self.assertEqual(final_state, State(messages=[1, 2, 4, 9]))

    def test_23_aggregator_with_conditional(self):
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
            if latest_state%3 == 0:
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
        final_state = executor.execute()
        self.assertEqual(final_state, State(messages=[0, 1, 3, 4, 7, 8, 9, 11, 12, 23, 24]))
    
    def test_24_retry_policy_behavior(self):
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
        executor = GraphExecutor(graph, initial_state, retry_policy=RetryPolicy(max_retries=5, delay=0.1, backoff=1))
        final_state = executor.execute()
        # Expect that after a few failures, the node eventually appends the call count (which should be 3)
        self.assertIn(3, final_state.messages)

    def test_25_max_supersteps_exceeded(self):
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
        with self.assertRaises(GraphExecutionError):
            executor.execute(max_supersteps=3)

    def test_26_toolnode_missing_description(self):
        # Define a tool method with no docstring and an empty description.
        def tool_method(state: State) -> State:
            state.messages.append(42)
            return state
        # Ensure no docstring and no description provided.
        tool_method.__doc__ = None
        tool_method.is_tool_method = True
        with self.assertRaises(EmptyToolNodeDescriptionError):
            # Attempt to create a ToolNode without a description.
            _ = ToolNode("tool", tool_method, description="")

    def test_27_successful_toolnode_execution(self):
        # Define a properly decorated tool method with a valid description.
        @tool_method
        def valid_tool(state: State) -> State:
            """A valid tool method that appends 999."""
            state.messages.append(999)
            return state
        builder = GraphBuilder()
        tool_node = ToolNode("tool", valid_tool, description="Appends 999 to state")
        builder.add_node(tool_node)
        builder.add_concrete_edge("start", "tool")
        builder.add_concrete_edge("tool", "end")
        graph = builder.build_graph()
        initial_state = State(messages=[])
        executor = GraphExecutor(graph, initial_state)
        final_state = executor.execute()
        self.assertIn(999, final_state.messages)

    def test_28_aggregator_invalid_output(self):
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
        with self.assertRaises((InvalidAggregatorActionError, GraphExecutionError)):
            executor.execute()

    def test_29_routing_function_invalid_output(self):
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
        with self.assertRaises((InvalidRoutingFunctionOutput, GraphExecutionError)):
            executor.execute()

    def test_30_node_action_invalid_output(self):
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
        with self.assertRaises((InvalideNodeActionOutput, GraphExecutionError)):
            executor.execute()

    def test_31_tool_method_not_decorated(self):
        # Define a tool method that is not decorated with the tool method marker.
        def not_decorated_tool(state: State) -> State:
            return state
        # Do not set the is_tool_method flag.
        with self.assertRaises(ToolMethodNotDecorated):
            _ = ToolNode("tool", not_decorated_tool, description="Has no proper decoration")

    def test_32_node_execution_timeout(self):
        # Define a node that sleeps longer than the allowed superstep timeout.
        @node_action
        def slow_node(state: State):
            time.sleep(2)  # Sleep 2 seconds, which is longer than the timeout we will set.
            state.messages.append(999)
            return state

        builder = GraphBuilder()
        builder.add_node(ProcessingNode("slow", slow_node))
        builder.add_concrete_edge("start", "slow")
        builder.add_concrete_edge("slow", "end")
        graph = builder.build_graph()
        initial_state = State(messages=[])
        # Set a very short timeout.
        executor = GraphExecutor(graph, initial_state)
        with self.assertRaises(GraphExecutionError) as cm:
            executor.execute(superstep_timeout=1)
        # Shutdown the executor to prevent pending tasks from logging after the test.
        executor.executor.shutdown(wait=False)
        self.assertIn("timed out", str(cm.exception))

    def test_33_aggregator_insufficient_states(self):
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

        with self.assertRaises(GraphExecutionError):
            executor.execute()

    def test_34_aggregator_state_isolation(self):
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
        final_state = executor.execute()
        # Ensure only the output state is modified
        self.assertIn("MODIFIED", final_state.messages)

    def test_35_routing_to_nonexistent_node(self):
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

        with self.assertRaises(GraphExecutionError) as cm:
            executor.execute()

        self.assertIn("ghost", str(cm.exception))

    def test_36_empty_state_messages(self):
        @node_action
        def noop(state: State):
            return state

        builder = GraphBuilder()
        builder.add_node(ProcessingNode("noop", noop))
        builder.add_concrete_edge("start", "noop")
        builder.add_concrete_edge("noop", "end")

        graph = builder.build_graph()
        executor = GraphExecutor(graph, State(messages=[]))
        final_state = executor.execute()

        self.assertEqual(final_state.messages, [])

    def test_37_mutated_shared_state(self):
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
        final_state = executor.execute()

        # Assert we only see one MUTATED, not duplication due to shared state mutation
        self.assertLessEqual(final_state.messages.count("MUTATED"), 1)
            
    def test_38_toolnode_docstring_suffices(self):
        @tool_method
        def documented_tool(state: State):
            """This tool works without an explicit description."""
            state.messages.append("OK")
            return state

        tool_node = ToolNode("doc_tool", documented_tool, description=None)
        builder = GraphBuilder()
        builder.add_node(tool_node)
        builder.add_concrete_edge("start", "doc_tool")
        builder.add_concrete_edge("doc_tool", "end")

        graph = builder.build_graph()
        executor = GraphExecutor(graph, State(messages=[]))
        final_state = executor.execute()
        self.assertIn("OK", final_state.messages)
    
    def test_39_single_input_to_aggregator(self):
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
        final_state = executor.execute()
        self.assertIn("solo", final_state.messages)
    
    def test_40_blank_routing_output(self):
        @routing_function
        def bad_router(state: State):
            return ""  # Invalid node ID

        builder = GraphBuilder()
        builder.add_node(ProcessingNode("n1", passThrough))
        builder.add_concrete_edge("start", "n1")
        builder.add_conditional_edge("n1", ["end"], bad_router)
        graph = builder.build_graph()

        executor = GraphExecutor(graph, State(messages=["blank"]))
        with self.assertRaises(GraphExecutionError) as cm:
            executor.execute()
        self.assertIn("''", str(cm.exception))  # check blank is part of error

    def test_41_aggregator_state_post_mutation_check(self):
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
        final_state = executor.execute()
        captured["ref"].messages.append("SNEAKY")  # post-mutation

        # Ensure original final_state is unaffected
        self.assertNotIn("SNEAKY", final_state.messages)

    def testv_01_conversion_test(self):
        @routing_function
        def dummy_router(state):
            return "agg"
        builder = GraphBuilder()
        proc_node = ProcessingNode("proc", passThrough)
        agg_node = AggregatorNode("agg", selectRandomState)
        builder.add_node(proc_node)
        builder.add_aggregator(agg_node)
        builder.add_concrete_edge("start", "proc")
        builder.add_conditional_edge("proc", ["agg", "end"], dummy_router)
        graph = builder.build_graph()
        rep_graph = RepresentationalGraph.from_graph(graph)
        self.assertIn("start", rep_graph.nodes)
        self.assertIn("proc", rep_graph.nodes)
        self.assertIn("agg", rep_graph.nodes)
        self.assertIn("end", rep_graph.nodes)
        self.assertEqual(len(rep_graph.edges), 1 + 2)
        concrete_edge = rep_graph.edges[0]
        self.assertEqual(concrete_edge.edge_type.name, "ConcreteEdgeRepresentation")
        for edge in rep_graph.edges[1:]:
            self.assertEqual(edge.edge_type.name, "ConditionalEdgeRepresentation")
        visualizer = GraphVisualizer(rep_graph)
        visualizer.visualize()
        

if __name__ == '__main__':
    unittest.main()
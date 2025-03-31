import time
import unittest
import matplotlib
# Use a non-interactive backend for testing so no window pops up.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import List
from core.GraphExecutorStatic import (
    State,
    DuplicateNodeError,
    NodeNotFoundError,
    EdgeExistsError,
    NodeActionNotDecoratedError,
    RoutingFunctionNotDecoratedError,
    GraphConfigurationError,
    ProcessingNode,
    AggregatorNode,
    ConditionalEdge,
    GraphBuilder,
    GraphExecutor,
    RepresentationalGraph,
    GraphVisualizer,
    passThrough,
    selectRandomState,
    node_action,
    aggregator_action,
    routing_function
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
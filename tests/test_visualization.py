import unittest
import matplotlib
# Use a non-interactive backend for testing so no window pops up.
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core.GraphExecutorStatic import (
    GraphBuilder,
    ProcessingNode,
    AggregatorNode,
    RepresentationalGraph,
    GraphVisualizer,
    # ConcreteEdge and ConditionalEdge classes are used internally by GraphBuilder.
)

# Dummy routing function for conditional edges.
def dummy_router(state):
    return "agg"

class TestRepresentationalGraph(unittest.TestCase):
    def setUp(self):
        # Build a simple graph:
        #   start -> proc (concrete edge)
        #   proc -> {agg, end} (conditional edge with two branches)
        builder = GraphBuilder()
        
        # Create a processing node and an aggregator node.
        proc_node = ProcessingNode("proc", lambda state: state)
        agg_node = AggregatorNode("agg")
        
        # Add nodes.
        builder.add_node(proc_node)
        builder.add_aggregator(agg_node)
        
        # Add edges:
        # Concrete edge: start -> proc.
        builder.add_concrete_edge("start", "proc")
        # Conditional edge: proc -> {agg, end}.
        builder.add_conditional_edge("proc", ["agg", "end"], dummy_router)
        
        # Build the graph.
        self.graph = builder.build_graph()
    
    def test_conversion(self):
        rep_graph = RepresentationalGraph.from_graph(self.graph)
        # Verify nodes exist.
        self.assertIn("start", rep_graph.nodes)
        self.assertIn("proc", rep_graph.nodes)
        self.assertIn("agg", rep_graph.nodes)
        self.assertIn("end", rep_graph.nodes)
        
        # Expected edges:
        #  - 1 concrete edge (start->proc)
        #  - 2 conditional edges (proc->agg and proc->end)
        self.assertEqual(len(rep_graph.edges), 1 + 2)
        
        # Check that the first edge is a concrete edge.
        concrete_edge = rep_graph.edges[0]
        self.assertEqual(concrete_edge.edge_type.name, "ConcreteEdgeRepresentation")
        
        # Check that the remaining edges are conditional.
        for edge in rep_graph.edges[1:]:
            self.assertEqual(edge.edge_type.name, "ConditionalEdgeRepresentation")
    
    def test_visualizer_runs(self):
        rep_graph = RepresentationalGraph.from_graph(self.graph)
        visualizer = GraphVisualizer(rep_graph)
        # Simply ensure visualize() runs without errors.
        try:
            visualizer.visualize()
        except Exception as e:
            self.fail(f"visualize() raised an exception unexpectedly: {e}")

if __name__ == "__main__":
    unittest.main()

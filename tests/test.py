import unittest
from core.GraphExecutorStatic import GraphBuilder, GraphExecutor, State, ProcessingNode

# A simple processing function that always marks the state as "passed"
def sample_node_func(state):
    state.data["sample"] = "passed"
    return state

class TestGraphExecutor(unittest.TestCase):
    def test_basic_execution(self):
        # Build a minimal graph: start -> sample -> end
        builder = GraphBuilder()
        sample_node = ProcessingNode("sample", sample_node_func)
        builder.add_node(sample_node)
        builder.add_concrete_edge("start", "sample")
        builder.add_concrete_edge("sample", "end")
        
        graph = builder.build_graph()
        initial_state = State(data={})
        executor = GraphExecutor(graph, initial_state, max_workers=1)
        final_state = executor.execute()
        
        # Verify that our sample node executed correctly.
        self.assertIn("sample", final_state.data)
        self.assertEqual(final_state.data["sample"], "passed")

if __name__ == '__main__':
    unittest.main()

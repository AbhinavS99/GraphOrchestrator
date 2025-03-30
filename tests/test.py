import sys
import time
import unittest
from core.GraphExecutorStatic import (
    GraphBuilder,
    GraphExecutor,
    State,
    ProcessingNode,
    GraphExecutionError,
    RetryPolicy,
    AggregatorNode,
)

def sample_node_func(state):
    """
    A simple processing function that marks the state as 'passed'.
    """
    state.data["sample"] = "passed"
    return state

class TestGraphExecutor(unittest.TestCase):
    """
    Unit tests for the GraphExecutor that also validate the retry mechanism.
    """

    def test_basic_execution(self):
        """
        Test basic graph execution without retry mechanism.
        Graph structure: start -> sample -> end.
        Expects that the sample node executes successfully.
        """
        builder = GraphBuilder()
        sample_node = ProcessingNode("sample", sample_node_func)
        builder.add_node(sample_node)
        builder.add_concrete_edge("start", "sample")
        builder.add_concrete_edge("sample", "end")
        
        graph = builder.build_graph()
        initial_state = State(data={})
        executor = GraphExecutor(graph, initial_state, max_workers=1)
        final_state = executor.execute()
        
        # Verify that the state contains the expected update.
        self.assertIn("sample", final_state.data)
        self.assertEqual(final_state.data["sample"], "passed")
    
    def test_retry_policy_success(self):
        """
        Test the retry mechanism on a node that fails a couple of times before succeeding.
        The flaky_function raises an exception on the first two attempts and succeeds on the third.
        The retry policy is set to allow 2 retries.
        """
        attempt_counter = {"count": 0}
        def flaky_function(state):
            if attempt_counter["count"] < 2:
                attempt_counter["count"] += 1
                raise Exception("Intentional failure")
            state.data["flaky"] = "succeeded"
            return state
        
        builder = GraphBuilder()
        flaky_node = ProcessingNode("flaky", flaky_function)
        builder.add_node(flaky_node)
        builder.add_concrete_edge("start", "flaky")
        builder.add_concrete_edge("flaky", "end")
        
        graph = builder.build_graph()
        initial_state = State(data={})
        retry_policy = RetryPolicy(max_retries=2, delay=0.1, backoff=1)
        executor = GraphExecutor(graph, initial_state, max_workers=1, retry_policy=retry_policy)
        final_state = executor.execute()
        
        # Verify that the node eventually succeeded after two retries.
        self.assertIn("flaky", final_state.data)
        self.assertEqual(final_state.data["flaky"], "succeeded")
        self.assertEqual(attempt_counter["count"], 2)
    
    def test_retry_policy_failure(self):
        """
        Test that the retry mechanism properly fails when the node always fails.
        The always_fail_function always raises an exception.
        The retry policy is set to allow 1 retry, so after retries are exhausted,
        a GraphExecutionError is expected.
        """
        def always_fail_function(state):
            raise Exception("Always fails")
        
        builder = GraphBuilder()
        failing_node = ProcessingNode("failing", always_fail_function)
        builder.add_node(failing_node)
        builder.add_concrete_edge("start", "failing")
        builder.add_concrete_edge("failing", "end")
        
        graph = builder.build_graph()
        initial_state = State(data={})
        retry_policy = RetryPolicy(max_retries=1, delay=0.1, backoff=1)
        executor = GraphExecutor(graph, initial_state, max_workers=1, retry_policy=retry_policy)
        
        # Expect a GraphExecutionError once the allowed retries are exhausted.
        with self.assertRaises(GraphExecutionError):
            executor.execute()

    def test_retry_backoff(self):
        """
        Test that the retry delay increases as expected based on the backoff factor.
        This test overrides time.sleep to record delays instead of actually sleeping.
        Expected delays: first delay is the initial delay and the next is multiplied by the backoff factor.
        """
        attempt_counter = {"count": 0}
        sleep_durations = []
        
        # Override time.sleep to record sleep durations.
        original_sleep = time.sleep
        def fake_sleep(duration):
            sleep_durations.append(duration)
        time.sleep = fake_sleep

        try:
            def flaky_function(state):
                if attempt_counter["count"] < 2:
                    attempt_counter["count"] += 1
                    raise Exception("Intentional failure")
                state.data["flaky"] = "succeeded"
                return state

            builder = GraphBuilder()
            flaky_node = ProcessingNode("flaky", flaky_function)
            builder.add_node(flaky_node)
            builder.add_concrete_edge("start", "flaky")
            builder.add_concrete_edge("flaky", "end")

            graph = builder.build_graph()
            initial_state = State(data={})
            # Set backoff factor to 2.0 to observe doubling of delay.
            retry_policy = RetryPolicy(max_retries=2, delay=0.1, backoff=2.0)
            executor = GraphExecutor(graph, initial_state, max_workers=1, retry_policy=retry_policy)
            final_state = executor.execute()

            # Verify the sleep durations: first 0.1 sec, then 0.1*2 = 0.2 sec.
            self.assertEqual(sleep_durations, [0.1, 0.2])
            self.assertEqual(attempt_counter["count"], 2)
            self.assertIn("flaky", final_state.data)
            self.assertEqual(final_state.data["flaky"], "succeeded")
        finally:
            time.sleep = original_sleep

    def test_aggregator_retry_success(self):
        """
        Test that a custom aggregator node that fails on its first attempt will be retried and eventually succeed.
        A custom aggregator node (FlakyAggregatorNode) is defined to fail on the first call to execute,
        then succeed on the retry, merging state from a succeeding processing node.
        """
        class FlakyAggregatorNode(AggregatorNode):
            """
            Custom aggregator node that fails on the first attempt.
            """
            def __init__(self, node_id: str):
                super().__init__(node_id)
                self.attempt_count = 0

            def execute(self, states):
                if self.attempt_count < 1:
                    self.attempt_count += 1
                    raise Exception("Aggregator intentional failure")
                return super().execute(states)
        
        builder = GraphBuilder()
        aggregator = FlakyAggregatorNode("aggregator")
        builder.add_aggregator(aggregator)
        sample_node = ProcessingNode("sample", sample_node_func)
        builder.add_node(sample_node)
        builder.add_concrete_edge("start", "sample")
        builder.add_concrete_edge("sample", "aggregator")
        builder.add_concrete_edge("aggregator", "end")
        
        graph = builder.build_graph()
        initial_state = State(data={})
        retry_policy = RetryPolicy(max_retries=2, delay=0.1, backoff=1)
        executor = GraphExecutor(graph, initial_state, max_workers=1, retry_policy=retry_policy)
        final_state = executor.execute()
        
        # Verify that the processing node executed and the aggregator retried once.
        self.assertIn("sample", final_state.data)
        self.assertEqual(final_state.data["sample"], "passed")
        self.assertEqual(aggregator.attempt_count, 1)

if __name__ == '__main__':
    unittest.main()

import asyncio
import copy
import logging
from typing import Dict, List, Optional
from collections import defaultdict

from graphorchestrator.core.retry import RetryPolicy
from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import GraphExecutionError
from graphorchestrator.nodes.nodes import AggregatorNode
from graphorchestrator.edges.concrete import ConcreteEdge
from graphorchestrator.edges.conditional import ConditionalEdge

class GraphExecutor:
    def __init__(self, graph, initial_state, max_workers: int = 4, retry_policy: Optional[RetryPolicy] = None):
        logging.info("graph=executor event=init max_workers=%d", max_workers)
        self.graph = graph
        self.initial_state = initial_state
        self.max_workers = max_workers
        self.active_states: Dict[str, List[State]] = defaultdict(list)
        self.active_states[graph.start_node.node_id].append(initial_state)
        self.retry_policy = retry_policy if retry_policy else RetryPolicy()
        self.semaphore = asyncio.Semaphore(self.max_workers)

    async def _execute_node_with_retry_async(self, node, input_data, retry_policy):
        attempt = 0
        delay = retry_policy.delay
        while attempt <= retry_policy.max_retries:
            async with self.semaphore:
                try:
                    logging.info(f"Running node={node.node_id} attempt={attempt}")
                    return await node.execute(input_data)
                except Exception as e:
                    if attempt == retry_policy.max_retries:
                        logging.error(f"Node '{node.node_id}' failed after {attempt+1} attempts: {e}")
                        raise e
                    logging.warning(f"Node '{node.node_id}' failed (attempt {attempt + 1}): {e}. Retrying in {delay:.2f}s.")
                    await asyncio.sleep(delay)
                    delay *= retry_policy.backoff
                    attempt += 1

    async def execute(self, max_supersteps: int = 100, superstep_timeout: float = 300.0) -> Optional[State]:
        logging.info("🚀 Graph execution started.")
        superstep = 0
        final_state = None

        while self.active_states and superstep < max_supersteps:
            logging.info(f"[STEP {superstep}] Nodes to execute: {list(self.active_states.keys())}")
            next_active_states: Dict[str, List[State]] = defaultdict(list)
            tasks = []

            for node_id, states in self.active_states.items():
                node = self.graph.nodes[node_id]
                input_data = states if isinstance(node, AggregatorNode) else copy.deepcopy(states[0])

                task = asyncio.create_task(
                    asyncio.wait_for(
                        self._execute_node_with_retry_async(node, input_data, self.retry_policy),
                        timeout=superstep_timeout
                    )
                )
                tasks.append((node_id, task))

            for node_id, task in tasks:
                try:
                    result_state = await task
                    node = self.graph.nodes[node_id]
                    logging.info(f"[STEP {superstep}] Node '{node_id}' execution complete.")

                    for edge in node.outgoing_edges:
                        if isinstance(edge, ConcreteEdge):
                            next_active_states[edge.sink.node_id].append(copy.deepcopy(result_state))
                            logging.info(f"[STEP {superstep}] {node_id} → {edge.sink.node_id} (via concrete)")
                        elif isinstance(edge, ConditionalEdge):
                            chosen_id = await edge.routing_function(result_state)
                            valid_ids = [sink.node_id for sink in edge.sinks]
                            if chosen_id not in valid_ids:
                                raise GraphExecutionError(node_id, f"Invalid routing output: '{chosen_id}'")
                            next_active_states[chosen_id].append(copy.deepcopy(result_state))
                            logging.info(f"[STEP {superstep}] {node_id} → {chosen_id} (via conditional router={edge.routing_function.__name__})")

                    if node_id == self.graph.end_node.node_id:
                        final_state = result_state

                except asyncio.TimeoutError:
                    logging.error(f"[STEP {superstep}] Node '{node_id}' timed out after {superstep_timeout:.1f}s.")
                    raise GraphExecutionError(node_id, f"Execution timed out after {superstep_timeout}s.")
                except Exception as e:
                    logging.error(f"[STEP {superstep}] Node '{node_id}' execution failed: {e}")
                    raise GraphExecutionError(node_id, str(e))

            self.active_states = next_active_states
            superstep += 1
            logging.info(f"[STEP {superstep}] Next active nodes: {list(self.active_states.keys())}")

        if superstep >= max_supersteps:
            logging.error("💥 Max supersteps reached — possible infinite loop.")
            raise GraphExecutionError("N/A", "Max supersteps reached")

        logging.info("✅ Graph execution completed successfully.")
        logging.info(f"🧾 Final state: \n{final_state}")
        return final_state

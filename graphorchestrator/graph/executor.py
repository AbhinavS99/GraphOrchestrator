import asyncio
import copy
import uuid
import getpass
import socket
from typing import Dict, List, Optional
from collections import defaultdict

from graphorchestrator.core.retry import RetryPolicy
from graphorchestrator.core.state import State
from graphorchestrator.core.checkpoint import CheckpointData
from graphorchestrator.core.exceptions import GraphExecutionError
from graphorchestrator.nodes.nodes import AggregatorNode
from graphorchestrator.edges.concrete import ConcreteEdge
from graphorchestrator.edges.conditional import ConditionalEdge
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC
from graphorchestrator.core.log_context import LogContext


class GraphExecutor:
    """
    GraphExecutor is responsible for executing a graph by iterating over its nodes in supersteps.
    It manages the execution flow, retry policies, checkpointing, and fallback mechanisms.

    Attributes:
        graph: The graph to execute.
        initial_state: The initial state of the graph execution.
        max_workers: The maximum number of concurrent node executions.
        retry_policy: The retry policy for node executions.
        checkpoint_path: The path to save/load checkpoints.
        checkpoint_every: The frequency (in supersteps) to save checkpoints.
        allow_fallback_from_checkpoint: Whether to fallback to the last checkpoint in case of timeout.
        active_states: The states of the active nodes in the current superstep.
        final_state: The final state of the execution, when the graph is fully executed.
    """

    def __init__(
        self,
        graph,
        initial_state,
        max_workers: int = 4,
        retry_policy: Optional[RetryPolicy] = None,
        checkpoint_path: Optional[str] = None,
        checkpoint_every: Optional[int] = None,
        allow_fallback_from_checkpoint: bool = False,
    ) -> None:
        """
        Initializes the GraphExecutor with the given parameters.

        Args:
            graph: The graph to execute.
            initial_state: The initial state of the graph execution.
            max_workers: The maximum number of concurrent node executions. Defaults to 4.
            retry_policy: The retry policy for node executions. Defaults to no retries.
            checkpoint_path: The path to save/load checkpoints. Defaults to None.
            checkpoint_every: The frequency (in supersteps) to save checkpoints. Defaults to None.
            allow_fallback_from_checkpoint: Whether to fallback to the last checkpoint in case of timeout. Defaults to False.
        """
        LogContext.set(
            {
                LC.RUN_ID: str(uuid.uuid4()),
                LC.GRAPH_NAME: getattr(graph, "name", None),
                LC.USER_ID: getpass.getuser(),
                LC.HOSTNAME: socket.gethostname(),
            }
        )
        log = GraphLogger.get()
        log.info(
            **wrap_constants(
                message="GraphExecutor initialized",
                **{
                    LC.EVENT_TYPE: "executor",
                    LC.ACTION: "executor_init",
                    LC.CUSTOM: {
                        "max_workers": max_workers,
                        "checkpoint_enabled": bool(checkpoint_path),
                        "checkpoint_every": checkpoint_every,
                        "allow_fallback_from_checkpoint": allow_fallback_from_checkpoint,
                        "retry_policy": {
                            "max_retries": (
                                retry_policy.max_retries if retry_policy else 0
                            ),
                            "delay": retry_policy.delay if retry_policy else 0,
                            "backoff": retry_policy.backoff if retry_policy else 1,
                        },
                    },
                },
            )
        )

        self.graph = graph
        self.initial_state = initial_state
        self.max_workers = max_workers
        self.active_states: Dict[str, List[State]] = defaultdict(list)
        self.active_states[graph.start_node.node_id].append(initial_state)
        self.retry_policy = (
            retry_policy if retry_policy else RetryPolicy(max_retries=0, delay=0)
        )
        self.semaphore = asyncio.Semaphore(self.max_workers)
        self.checkpoint_path = checkpoint_path
        self.checkpoint_every = checkpoint_every
        self.superstep = 0
        self.final_state = None
        self.allow_fallback_from_checkpoint = allow_fallback_from_checkpoint
        self.already_retried_from_checkpoint = False

        if self.allow_fallback_from_checkpoint and not self.checkpoint_path:
            log.error(
                **wrap_constants(
                    message="Checkpoint fallback enabled without path",
                    **{
                        LC.EVENT_TYPE: "executor",
                        LC.ACTION: "executor_init_failed",
                        LC.CUSTOM: {
                            "reason": "allow_fallback_from_checkpoint=True but checkpoint_path=None"
                        },
                    },
                )
            )
            raise GraphExecutionError(
                node_id="GraphExecutor",
                message="Fallback from checkpoint is enabled, but no checkpoint_path is provided.",
            )

    def to_checkpoint(self) -> CheckpointData:
        """
        Creates a CheckpointData object representing the current state of the graph execution.

        Returns:
            A CheckpointData object.
        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="Serializing current graph state into checkpoint",
                **{
                    LC.EVENT_TYPE: "executor",
                    LC.ACTION: "create_checkpoint",
                    LC.SUPERSTEP: self.superstep,
                    LC.CUSTOM: {
                        "active_node_ids": list(self.active_states.keys()),
                        "final_state_message_count": (
                            len(self.final_state.messages) if self.final_state else None
                        ),
                        "max_workers": self.max_workers,
                        "retry_policy": {
                            "max_retries": self.retry_policy.max_retries,
                            "delay": self.retry_policy.delay,
                            "backoff": self.retry_policy.backoff,
                        },
                    },
                },
            )
        )

        return CheckpointData(
            graph=self.graph,
            initial_state=self.initial_state,
            active_states=self.active_states,
            superstep=self.superstep,
            final_state=self.final_state,
            retry_policy=self.retry_policy,
            max_workers=self.max_workers,
        )

    @classmethod
    def from_checkpoint(
        cls,
        chkpt: CheckpointData,
        checkpoint_path: Optional[str] = None,
        checkpoint_every: Optional[int] = None,
    ):
        """
        Creates a GraphExecutor object from a CheckpointData object.

        Args:
            chkpt: The CheckpointData object to restore from.
            checkpoint_path: The path to save/load checkpoints. Defaults to None.
            checkpoint_every: The frequency (in supersteps) to save checkpoints. Defaults to None.

        Returns:
            A GraphExecutor object restored from the checkpoint.

        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="Restoring executor from checkpoint",
                **{
                    LC.EVENT_TYPE: "executor",
                    LC.ACTION: "restore_from_checkpoint",
                    LC.SUPERSTEP: chkpt.superstep,
                    LC.CUSTOM: {
                        "active_node_ids": list(chkpt.active_states.keys()),
                        "final_state_message_count": (
                            len(chkpt.final_state.messages)
                            if chkpt.final_state
                            else None
                        ),
                        "max_workers": chkpt.max_workers,
                        "checkpoint_path": checkpoint_path,
                        "checkpoint_every": checkpoint_every,
                    },
                },
            )
        )

        executor = cls(
            graph=chkpt.graph,
            initial_state=chkpt.initial_state,
            max_workers=chkpt.max_workers,
            retry_policy=chkpt.retry_policy,
            checkpoint_path=checkpoint_path,
            checkpoint_every=checkpoint_every,
        )
        executor.active_states = chkpt.active_states
        executor.superstep = chkpt.superstep
        executor.final_state = chkpt.final_state
        return executor

    async def _execute_node_with_retry_async(
        self, node, input_data, retry_policy
    ) -> None:
        """
        Executes a node with the given input data, applying the retry policy.
        This method is async and uses a semaphore to limit concurrency.

        Args:
            node: The node to execute.
            input_data: The input data for the node.
            retry_policy: The retry policy to apply.

        Raises:
            Exception: If the node execution fails after all retries.
        """
        log = GraphLogger.get()

        retry_policy = (
            node.retry_policy if node.retry_policy is not None else retry_policy
        )
        attempt = 0
        delay = retry_policy.delay

        while attempt <= retry_policy.max_retries:
            async with self.semaphore:
                try:
                    log.info(
                        **wrap_constants(
                            message="Executing node with retry",
                            **{
                                LC.EVENT_TYPE: "node",
                                LC.ACTION: "node_execution_attempt",
                                LC.NODE_ID: node.node_id,
                                LC.RETRY_COUNT: attempt,
                                LC.MAX_RETRIES: retry_policy.max_retries,
                                LC.RETRY_DELAY: delay,
                            },
                        )
                    )

                    return await node.execute(input_data)

                except Exception as e:
                    if attempt == retry_policy.max_retries:
                        log.error(
                            **wrap_constants(
                                message="Node execution failed after max retries",
                                **{
                                    LC.EVENT_TYPE: "node",
                                    LC.ACTION: "node_execution_failed",
                                    LC.NODE_ID: node.node_id,
                                    LC.RETRY_COUNT: attempt,
                                    LC.MAX_RETRIES: retry_policy.max_retries,
                                    LC.CUSTOM: {"error": str(e)},
                                },
                            )
                        )
                        raise e

                    log.warning(
                        **wrap_constants(
                            message="Node execution failed — will retry",
                            **{
                                LC.EVENT_TYPE: "node",
                                LC.ACTION: "node_retry_scheduled",
                                LC.NODE_ID: node.node_id,
                                LC.RETRY_COUNT: attempt,
                                LC.MAX_RETRIES: retry_policy.max_retries,
                                LC.RETRY_DELAY: delay,
                                LC.CUSTOM: {"error": str(e)},
                            },
                        )
                    )

                    await asyncio.sleep(delay)
                    delay *= retry_policy.backoff
                    attempt += 1

    async def execute(
        self, max_supersteps: int = 100, superstep_timeout: float = 300.0
    ) -> Optional[State]:
        """
        Executes the graph up to a maximum number of supersteps.

        Args:
            max_supersteps: The maximum number of supersteps to execute. Defaults to 100.
            superstep_timeout: The timeout (in seconds) for each superstep. Defaults to 300.0.

        Returns:
            The final state of the execution, if the graph completed successfully.
        Raises:
             GraphExecutionError: if the max_supersteps are reach or any error is encountered in the flow
        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="Graph execution started",
                **{
                    LC.EVENT_TYPE: "executor",
                    LC.ACTION: "execution_start",
                    LC.CUSTOM: {
                        "max_supersteps": max_supersteps,
                        "timeout_per_superstep": superstep_timeout,
                    },
                },
            )
        )

        final_state = None

        while self.active_states and self.superstep < max_supersteps:
            log.info(
                **wrap_constants(
                    message=f"Superstep {self.superstep} execution",
                    **{
                        LC.EVENT_TYPE: "executor",
                        LC.ACTION: "superstep_started",
                        LC.SUPERSTEP: self.superstep,
                        LC.CUSTOM: {"active_nodes": list(self.active_states.keys())},
                    },
                )
            )

            next_active_states: Dict[str, List[State]] = defaultdict(list)
            tasks = []

            for node_id, states in self.active_states.items():
                node = self.graph.nodes[node_id]
                input_data = (
                    states
                    if isinstance(node, AggregatorNode)
                    else copy.deepcopy(states[0])
                )

                task = asyncio.create_task(
                    asyncio.wait_for(
                        self._execute_node_with_retry_async(
                            node, input_data, self.retry_policy
                        ),
                        timeout=superstep_timeout,
                    )
                )
                tasks.append((node_id, task, input_data))

            for node_id, task, original_input in tasks:
                node = self.graph.nodes[node_id]
                try:
                    result_state = await task
                    log.info(
                        **wrap_constants(
                            message="Node execution complete",
                            **{
                                LC.EVENT_TYPE: "node",
                                LC.ACTION: "node_execution_complete",
                                LC.SUPERSTEP: self.superstep,
                                LC.NODE_ID: node_id,
                            },
                        )
                    )

                except asyncio.TimeoutError:
                    log.error(
                        **wrap_constants(
                            message="Node execution timed out",
                            **{
                                LC.EVENT_TYPE: "node",
                                LC.ACTION: "timeout",
                                LC.SUPERSTEP: self.superstep,
                                LC.NODE_ID: node_id,
                                LC.TIMEOUT: superstep_timeout,
                            },
                        )
                    )

                    if (
                        self.allow_fallback_from_checkpoint
                        and not self.already_retried_from_checkpoint
                    ):
                        log.warning(
                            **wrap_constants(
                                message="Falling back to checkpoint after timeout",
                                **{
                                    LC.EVENT_TYPE: "executor",
                                    LC.ACTION: "fallback_to_checkpoint",
                                },
                            )
                        )
                        chkpt = CheckpointData.load(self.checkpoint_path)
                        fallback_executor = GraphExecutor.from_checkpoint(
                            chkpt,
                            checkpoint_path=self.checkpoint_path,
                            checkpoint_every=self.checkpoint_every,
                        )
                        fallback_executor.allow_fallback_from_checkpoint = False
                        fallback_executor.already_retried_from_checkpoint = True
                        return await fallback_executor.execute(
                            max_supersteps=max_supersteps,
                            superstep_timeout=superstep_timeout,
                        )

                    log.error(
                        **wrap_constants(
                            message="No checkpoint fallback available",
                            **{
                                LC.EVENT_TYPE: "executor",
                                LC.ACTION: "no_fallback",
                                LC.NODE_ID: node_id,
                            },
                        )
                    )
                    raise GraphExecutionError(
                        node_id, f"Execution timed out after {superstep_timeout}s."
                    )

                except Exception as e:
                    fallback_id = getattr(node, "fallback_node_id", None)
                    if fallback_id:
                        fallback_node = self.graph.nodes[fallback_id]
                        log.warning(
                            **wrap_constants(
                                message="Fallback invoked due to node failure",
                                **{
                                    LC.EVENT_TYPE: "executor",
                                    LC.ACTION: "fallback_invoked",
                                    LC.SOURCE_NODE: node_id,
                                    LC.FALLBACK_NODE: fallback_id,
                                    LC.CUSTOM: {"reason": str(e)},
                                },
                            )
                        )
                        try:
                            result_state = await asyncio.wait_for(
                                self._execute_node_with_retry_async(
                                    fallback_node, original_input, self.retry_policy
                                ),
                                timeout=superstep_timeout,
                            )
                            log.info(
                                **wrap_constants(
                                    message="Fallback node execution succeeded",
                                    **{
                                        LC.EVENT_TYPE: "executor",
                                        LC.ACTION: "fallback_success",
                                        LC.FALLBACK_NODE: fallback_id,
                                    },
                                )
                            )
                        except Exception as fallback_error:
                            log.error(
                                **wrap_constants(
                                    message="Fallback node execution failed",
                                    **{
                                        LC.EVENT_TYPE: "executor",
                                        LC.ACTION: "fallback_failed",
                                        LC.FALLBACK_NODE: fallback_id,
                                        LC.CUSTOM: {"reason": str(fallback_error)},
                                    },
                                )
                            )
                            raise GraphExecutionError(
                                fallback_id, f"Fallback node failed: {fallback_error}"
                            )
                    else:
                        log.error(
                            **wrap_constants(
                                message="Node execution failed without fallback",
                                **{
                                    LC.EVENT_TYPE: "node",
                                    LC.ACTION: "node_execution_failed",
                                    LC.NODE_ID: node_id,
                                    LC.SUPERSTEP: self.superstep,
                                    LC.CUSTOM: {"error": str(e)},
                                },
                            )
                        )
                        raise GraphExecutionError(node_id, str(e))

                # Transition state to next active nodes
                for edge in node.outgoing_edges:
                    if isinstance(edge, ConcreteEdge):
                        next_active_states[edge.sink.node_id].append(
                            copy.deepcopy(result_state)
                        )
                        log.info(
                            **wrap_constants(
                                message="Edge transition (concrete)",
                                **{
                                    LC.EVENT_TYPE: "edge",
                                    LC.ACTION: "concrete_edge_transition",
                                    LC.SOURCE_NODE: node_id,
                                    LC.SINK_NODE: edge.sink.node_id,
                                },
                            )
                        )
                    elif isinstance(edge, ConditionalEdge):
                        chosen_id = await edge.routing_function(result_state)
                        valid_ids = [sink.node_id for sink in edge.sinks]
                        if chosen_id not in valid_ids:
                            raise GraphExecutionError(
                                node.node_id, f"Invalid routing output: '{chosen_id}'"
                            )
                        next_active_states[chosen_id].append(
                            copy.deepcopy(result_state)
                        )
                        log.info(
                            **wrap_constants(
                                message="Edge transition (conditional)",
                                **{
                                    LC.EVENT_TYPE: "edge",
                                    LC.ACTION: "conditional_edge_transition",
                                    LC.SOURCE_NODE: node_id,
                                    LC.SINK_NODE: chosen_id,
                                    LC.ROUTER_FUNC: edge.routing_function.__name__,
                                },
                            )
                        )

                if node_id == self.graph.end_node.node_id:
                    final_state = result_state

            self.active_states = next_active_states
            self.superstep += 1

            # 💾 Auto-checkpointing
            if (
                self.checkpoint_path
                and self.checkpoint_every
                and self.superstep % self.checkpoint_every == 0
            ):
                log.info(
                    **wrap_constants(
                        message="Auto-saving checkpoint",
                        **{
                            LC.EVENT_TYPE: "executor",
                            LC.ACTION: "auto_checkpoint",
                            LC.SUPERSTEP: self.superstep,
                            LC.CUSTOM: {"checkpoint_path": self.checkpoint_path},
                        },
                    )
                )
                self.to_checkpoint().save(self.checkpoint_path)

            log.info(
                **wrap_constants(
                    message="Superstep completed",
                    **{
                        LC.EVENT_TYPE: "executor",
                        LC.ACTION: "superstep_complete",
                        LC.SUPERSTEP: self.superstep,
                        LC.CUSTOM: {
                            "next_active_nodes": list(self.active_states.keys())
                        },
                    },
                )
            )

        if self.superstep >= max_supersteps:
            log.error(
                **wrap_constants(
                    message="Max supersteps reached — possible infinite loop",
                    **{LC.EVENT_TYPE: "executor", LC.ACTION: "max_supersteps_exceeded"},
                )
            )
            raise GraphExecutionError("N/A", "Max supersteps reached")

        log.info(
            **wrap_constants(
                message="Graph execution completed successfully",
                **{LC.EVENT_TYPE: "executor", LC.ACTION: "execution_complete"},
            )
        )

        log.info(
            **wrap_constants(
                message="Final state summary",
                **{
                    LC.EVENT_TYPE: "executor",
                    LC.ACTION: "final_state",
                    LC.CUSTOM: {
                        "message_count": (
                            len(final_state.messages) if final_state else None
                        )
                    },
                },
            )
        )

        return final_state

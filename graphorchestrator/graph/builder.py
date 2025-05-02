import logging
from typing import Callable, List, Optional

from graphorchestrator.core.retry import RetryPolicy
from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import (
    DuplicateNodeError,
    NodeNotFoundError,
    EdgeExistsError,
    GraphConfigurationError,
)
from graphorchestrator.nodes.nodes import ProcessingNode, AggregatorNode
from graphorchestrator.edges.concrete import ConcreteEdge
from graphorchestrator.edges.conditional import ConditionalEdge
from graphorchestrator.graph.graph import Graph
from graphorchestrator.decorators.builtin_actions import passThrough
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class GraphBuilder:
    """
    GraphBuilder is a utility class for constructing complex directed graphs.

    It supports adding various types of nodes (ProcessingNode, AggregatorNode) and
    edges (ConcreteEdge, ConditionalEdge) to define the flow and logic of a
    processing pipeline. It also handles error handling and logging.
    """

    def __init__(self, name: Optional[str] = "graph"):
        GraphLogger.get().info(
            **wrap_constants(
                message="GraphBuilder initialized",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "builder_init",
                    LC.CUSTOM: {"graph_name": name},
                }
            )
        )

        start_node = ProcessingNode("start", passThrough)
        end_node = ProcessingNode("end", passThrough)
        self.graph = Graph(start_node, end_node, name)
        self.add_node(start_node)
        self.add_node(end_node)

    def add_node(self, node):
        """
        Adds a node to the graph.

        Args:
            node: The node to be added.
        Raises:
             DuplicateNodeError: if there is already a node with the same id in the graph.
        """
        log = GraphLogger.get()

        log.debug(
            **wrap_constants(
                message="Attempting to add node to graph",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "add_node_attempt",
                    LC.NODE_ID: node.node_id,
                }
            )
        )

        if node.node_id in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Duplicate node detected",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "duplicate_node",
                        LC.NODE_ID: node.node_id,
                    }
                )
            )
            raise DuplicateNodeError(node.node_id)

        self.graph.nodes[node.node_id] = node

        log.info(
            **wrap_constants(
                message="Node successfully added to graph",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "node_added",
                    LC.NODE_ID: node.node_id,
                    LC.NODE_TYPE: node.__class__.__name__,
                }
            )
        )

    def set_fallback_node(self, node_id: str, fallback_node_id: str):
        """
        Sets a fallback node for a given node.

        In case of failure of the node, the graph will execute the fallback node.

        Args:
            node_id: The ID of the node for which to set a fallback.
            fallback_node_id: The ID of the fallback node.

        Raises:
            NodeNotFoundError: if the node or fallback node does not exist in the graph.
        """
        log = GraphLogger.get()

        log.debug(
            **wrap_constants(
                message="Attempting to set fallback node",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "set_fallback_attempt",
                    LC.NODE_ID: node_id,
                    LC.FALLBACK_NODE: fallback_node_id,
                }
            )
        )

        if node_id not in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Primary node not found for fallback assignment",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "fallback_assignment_failed",
                        LC.NODE_ID: node_id,
                        LC.FALLBACK_NODE: fallback_node_id,
                        LC.CUSTOM: {"reason": "node_id does not exist"},
                    }
                )
            )
            raise NodeNotFoundError(node_id)

        if fallback_node_id not in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Fallback node not found in graph",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "fallback_assignment_failed",
                        LC.NODE_ID: node_id,
                        LC.FALLBACK_NODE: fallback_node_id,
                        LC.CUSTOM: {"reason": "fallback_node_id does not exist"},
                    }
                )
            )
            raise NodeNotFoundError(fallback_node_id)

        self.graph.nodes[node_id].set_fallback(fallback_node_id)

        log.info(
            **wrap_constants(
                message="Fallback node set successfully",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "fallback_assigned",
                    LC.NODE_ID: node_id,
                    LC.FALLBACK_NODE: fallback_node_id,
                }
            )
        )

    def set_node_retry_policy(self, node_id: str, retry_policy: RetryPolicy) -> None:
        """
        Sets a retry policy for a given node.

        The node will retry upon failure as per the given policy.

        Args:
            node_id: The ID of the node for which to set the retry policy.
            retry_policy: The retry policy to set.
        Raises:
            NodeNotFoundError: if the node does not exist in the graph.
        """
        log = GraphLogger.get()

        log.debug(
            **wrap_constants(
                message="Attempting to set retry policy for node",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "set_retry_policy_attempt",
                    LC.NODE_ID: node_id,
                    LC.CUSTOM: {
                        "max_retries": retry_policy.max_retries,
                        "delay": retry_policy.delay,
                        "backoff": retry_policy.backoff,
                    },
                }
            )
        )

        if node_id not in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Cannot set retry policy — node not found",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "set_retry_policy_failed",
                        LC.NODE_ID: node_id,
                        LC.CUSTOM: {"reason": "node_id does not exist"},
                    }
                )
            )
            raise NodeNotFoundError(node_id)

        self.graph.nodes[node_id].set_retry_policy(retry_policy)

        log.info(
            **wrap_constants(
                message="Retry policy set successfully",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "retry_policy_assigned",
                    LC.NODE_ID: node_id,
                    LC.CUSTOM: {
                        "max_retries": retry_policy.max_retries,
                        "delay": retry_policy.delay,
                        "backoff": retry_policy.backoff,
                    },
                }
            )
        )

    def add_aggregator(self, aggregator: AggregatorNode):
        """
        Adds an aggregator node to the graph.

        Args:
            aggregator: The aggregator node to add.
        Raises:
             DuplicateNodeError: if there is already a node with the same id in the graph.
        """
        log = GraphLogger.get()

        log.debug(
            **wrap_constants(
                message="Attempting to add aggregator node to graph",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "add_aggregator_attempt",
                    LC.NODE_ID: aggregator.node_id,
                    LC.NODE_TYPE: "AggregatorNode",
                }
            )
        )

        if aggregator.node_id in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Duplicate aggregator node detected",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "duplicate_node",
                        LC.NODE_ID: aggregator.node_id,
                        LC.NODE_TYPE: "AggregatorNode",
                    }
                )
            )
            raise DuplicateNodeError(aggregator.node_id)

        self.graph.nodes[aggregator.node_id] = aggregator

        log.info(
            **wrap_constants(
                message="Aggregator node registered in graph",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "aggregator_registered",
                    LC.NODE_ID: aggregator.node_id,
                    LC.NODE_TYPE: "AggregatorNode",
                }
            )
        )

    def add_concrete_edge(self, source_id: str, sink_id: str):
        """
        Adds a concrete edge between two nodes.

        Args:
            source_id: The ID of the source node.
            sink_id: The ID of the sink node.

        Raises:
            NodeNotFoundError: if the source or sink node does not exist in the graph.
            EdgeExistsError: if an edge already exists between the source and sink.
        """
        log = GraphLogger.get()

        log.debug(
            **wrap_constants(
                message="Attempting to add concrete edge",
                **{
                    LC.EVENT_TYPE: "edge",
                    LC.ACTION: "add_concrete_edge_attempt",
                    LC.SOURCE_NODE: source_id,
                    LC.SINK_NODE: sink_id,
                    LC.EDGE_TYPE: "concrete",
                }
            )
        )

        if source_id not in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Concrete edge source node not found",
                    **{
                        LC.EVENT_TYPE: "edge",
                        LC.ACTION: "add_concrete_edge_failed",
                        LC.SOURCE_NODE: source_id,
                        LC.SINK_NODE: sink_id,
                        LC.CUSTOM: {"reason": "source_id not in graph"},
                    }
                )
            )
            raise NodeNotFoundError(source_id)

        if source_id == "end":
            raise GraphConfigurationError("End cannot be the source of a concrete edge")

        if sink_id not in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Concrete edge sink node not found",
                    **{
                        LC.EVENT_TYPE: "edge",
                        LC.ACTION: "add_concrete_edge_failed",
                        LC.SOURCE_NODE: source_id,
                        LC.SINK_NODE: sink_id,
                        LC.CUSTOM: {"reason": "sink_id not in graph"},
                    }
                )
            )
            raise NodeNotFoundError(sink_id)

        if sink_id == "start":
            raise GraphConfigurationError("Start cannot be a sink of concrete edge")

        source = self.graph.nodes[source_id]
        sink = self.graph.nodes[sink_id]

        for edge in self.graph.concrete_edges:
            if edge.source == source and edge.sink == sink:
                log.error(
                    **wrap_constants(
                        message="Duplicate concrete edge detected",
                        **{
                            LC.EVENT_TYPE: "edge",
                            LC.ACTION: "duplicate_edge",
                            LC.SOURCE_NODE: source_id,
                            LC.SINK_NODE: sink_id,
                        }
                    )
                )
                raise EdgeExistsError(source_id, sink_id)

        for cond_edge in self.graph.conditional_edges:
            if cond_edge.source == source and sink in cond_edge.sinks:
                log.error(
                    **wrap_constants(
                        message="Edge conflicts with existing conditional edge",
                        **{
                            LC.EVENT_TYPE: "edge",
                            LC.ACTION: "conflict_with_conditional_edge",
                            LC.SOURCE_NODE: source_id,
                            LC.SINK_NODE: sink_id,
                        }
                    )
                )
                raise EdgeExistsError(source_id, sink_id)

        edge = ConcreteEdge(source, sink)
        self.graph.concrete_edges.append(edge)
        source.outgoing_edges.append(edge)
        sink.incoming_edges.append(edge)

        log.info(
            **wrap_constants(
                message="Concrete edge successfully added",
                **{
                    LC.EVENT_TYPE: "edge",
                    LC.ACTION: "concrete_edge_added",
                    LC.SOURCE_NODE: source_id,
                    LC.SINK_NODE: sink_id,
                    LC.EDGE_TYPE: "concrete",
                }
            )
        )

    def add_conditional_edge(
        self, source_id: str, sink_ids: List[str], router: Callable[[State], str]
    ):
        """
        Adds a conditional edge between a source node and multiple sink nodes,
        using a router function to determine the sink based on the state.

        Args:
            source_id: The ID of the source node.
            sink_ids: A list of IDs of the possible sink nodes.
            router: A function that takes a State object and returns the ID of the
                    chosen sink node.

        Raises:
            NodeNotFoundError: if the source or sink node does not exist in the graph.
        """
        log = GraphLogger.get()

        log.debug(
            **wrap_constants(
                message="Attempting to add conditional edge",
                **{
                    LC.EVENT_TYPE: "edge",
                    LC.ACTION: "add_conditional_edge_attempt",
                    LC.SOURCE_NODE: source_id,
                    LC.SINK_NODE: sink_ids,
                    LC.EDGE_TYPE: "conditional",
                    LC.ROUTER_FUNC: router.__name__,
                }
            )
        )

        if source_id not in self.graph.nodes:
            log.error(
                **wrap_constants(
                    message="Conditional edge source node not found",
                    **{
                        LC.EVENT_TYPE: "edge",
                        LC.ACTION: "add_conditional_edge_failed",
                        LC.SOURCE_NODE: source_id,
                        LC.SINK_NODE: sink_ids,
                        LC.CUSTOM: {"reason": "source_id not in graph"},
                    }
                )
            )
            raise NodeNotFoundError(source_id)

        if source_id == "end":
            raise GraphConfigurationError(
                "End cannot be the source of a conditional edge"
            )

        source = self.graph.nodes[source_id]
        sinks = []

        for sink_id in sink_ids:
            if sink_id not in self.graph.nodes:
                log.error(
                    **wrap_constants(
                        message="Conditional edge sink node not found",
                        **{
                            LC.EVENT_TYPE: "edge",
                            LC.ACTION: "add_conditional_edge_failed",
                            LC.SOURCE_NODE: source_id,
                            LC.SINK_NODE: sink_id,
                            LC.CUSTOM: {"reason": "sink_id not in graph"},
                        }
                    )
                )
                raise NodeNotFoundError(sink_id)

            if sink_id == "start":
                raise GraphConfigurationError(
                    "Start cannot be a sink of conditional edge"
                )

            sinks.append(self.graph.nodes[sink_id])

        for edge in self.graph.concrete_edges:
            if edge.source == source and edge.sink in sinks:
                log.error(
                    **wrap_constants(
                        message="Conflict with existing concrete edge",
                        **{
                            LC.EVENT_TYPE: "edge",
                            LC.ACTION: "conflict_with_concrete_edge",
                            LC.SOURCE_NODE: source_id,
                            LC.SINK_NODE: edge.sink.node_id,
                        }
                    )
                )
                raise EdgeExistsError(source_id, edge.sink.node_id)

        for cond_edge in self.graph.conditional_edges:
            if cond_edge.source == source:
                for s in sinks:
                    if s in cond_edge.sinks:
                        log.error(
                            **wrap_constants(
                                message="Duplicate conditional edge branch detected",
                                **{
                                    LC.EVENT_TYPE: "edge",
                                    LC.ACTION: "duplicate_conditional_branch",
                                    LC.SOURCE_NODE: source_id,
                                    LC.SINK_NODE: s.node_id,
                                }
                            )
                        )
                        raise EdgeExistsError(source_id, s.node_id)

        edge = ConditionalEdge(source, sinks, router)
        self.graph.conditional_edges.append(edge)
        source.outgoing_edges.append(edge)
        for sink in sinks:
            sink.incoming_edges.append(edge)

        log.info(
            **wrap_constants(
                message="Conditional edge successfully added",
                **{
                    LC.EVENT_TYPE: "edge",
                    LC.ACTION: "conditional_edge_added",
                    LC.SOURCE_NODE: source_id,
                    LC.SINK_NODE: [s.node_id for s in sinks],
                    LC.EDGE_TYPE: "conditional",
                    LC.ROUTER_FUNC: router.__name__,
                }
            )
        )

    def build_graph(self) -> Graph:
        """
        Builds and validates the graph.

        Performs a validation of the graph prior to build.

        Returns:
            The constructed Graph object.
        Raises:
            GraphConfigurationError: if the configuration of the graph is not valid.
        """
        log = GraphLogger.get()

        log.debug(
            **wrap_constants(
                message="Validating graph before build",
                **{LC.EVENT_TYPE: "graph", LC.ACTION: "build_graph_validation_start"}
            )
        )

        start_node = self.graph.start_node

        if any(isinstance(e, ConditionalEdge) for e in start_node.outgoing_edges):
            log.error(
                **wrap_constants(
                    message="Start node has a conditional edge — invalid graph",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "build_graph_failed",
                        LC.CUSTOM: {"reason": "start node has conditional edge"},
                    }
                )
            )
            raise GraphConfigurationError("Start node cannot have a conditional edge")

        if not any(isinstance(e, ConcreteEdge) for e in start_node.outgoing_edges):
            log.error(
                **wrap_constants(
                    message="Start node missing concrete edge — invalid graph",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "build_graph_failed",
                        LC.CUSTOM: {
                            "reason": "start node must have at least one concrete edge"
                        },
                    }
                )
            )
            raise GraphConfigurationError(
                "Start node must have at least one outgoing concrete edge"
            )

        if not self.graph.end_node.incoming_edges:
            log.error(
                **wrap_constants(
                    message="End node has no incoming edges — invalid graph",
                    **{
                        LC.EVENT_TYPE: "graph",
                        LC.ACTION: "build_graph_failed",
                        LC.CUSTOM: {
                            "reason": "end node must have at least one incoming edge"
                        },
                    }
                )
            )
            raise GraphConfigurationError(
                "End node must have at least one incoming edge"
            )

        log.info(
            **wrap_constants(
                message="Graph successfully built",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "graph_built",
                    LC.CUSTOM: {
                        "node_count": len(self.graph.nodes),
                        "concrete_edges": len(self.graph.concrete_edges),
                        "conditional_edges": len(self.graph.conditional_edges),
                    },
                }
            )
        )

        return self.graph

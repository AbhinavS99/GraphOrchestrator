import logging
from typing import Callable, List

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import (
    DuplicateNodeError, NodeNotFoundError,
    EdgeExistsError, GraphConfigurationError
)
from graphorchestrator.nodes.nodes import ProcessingNode, AggregatorNode
from graphorchestrator.edges.concrete import ConcreteEdge
from graphorchestrator.edges.conditional import ConditionalEdge
from graphorchestrator.graph.graph import Graph
from graphorchestrator.decorators.builtin_actions import passThrough

class GraphBuilder:
    def __init__(self):
        logging.info("graph=builder event=init")
        start_node = ProcessingNode("start", passThrough)
        end_node = ProcessingNode("end", passThrough)
        self.graph = Graph(start_node, end_node)
        self.add_node(start_node)
        self.add_node(end_node)

    def add_node(self, node):
        logging.debug(f"graph=builder event=add_node node_id={node.node_id}")
        if node.node_id in self.graph.nodes:
            logging.error(f"graph=builder event=duplicate_node node_id={node.node_id}")
            raise DuplicateNodeError(node.node_id)
        self.graph.nodes[node.node_id] = node
        logging.info(f"graph=builder event=node_added node_id={node.node_id}")

    def set_fallback_node(self, node_id: str, fallback_node_id: str):
        if node_id not in self.graph.nodes:
            raise NodeNotFoundError(node_id)
        if fallback_node_id not in self.graph.nodes:
            raise NodeNotFoundError(fallback_node_id)
        self.graph.nodes[node_id].set_fallback(fallback_node_id)
        logging.debug(f"graph=builder event=set_fallback_node node={node_id} fallback={fallback_node_id}")

    def add_aggregator(self, aggregator: AggregatorNode):
        logging.debug(f"graph=builder event=add_aggregator node_id={aggregator.node_id}")
        self.add_node(aggregator)

    def add_concrete_edge(self, source_id: str, sink_id: str):
        logging.debug(f"graph=builder event=add_concrete_edge source={source_id} sink={sink_id}")
        if source_id not in self.graph.nodes:
            raise NodeNotFoundError(source_id)
        if source_id == "end":
            raise GraphConfigurationError("End cannot be the source of a concrete edge")
        if sink_id not in self.graph.nodes:
            raise NodeNotFoundError(sink_id)
        if sink_id == "start":
            raise GraphConfigurationError("Start cannot be a sink of concrete edge")

        source = self.graph.nodes[source_id]
        sink = self.graph.nodes[sink_id]

        for edge in self.graph.concrete_edges:
            if edge.source == source and edge.sink == sink:
                logging.error(f"graph=builder event=duplicate_edge source={source_id} sink={sink_id}")
                raise EdgeExistsError(source_id, sink_id)

        for cond_edge in self.graph.conditional_edges:
            if cond_edge.source == source and sink in cond_edge.sinks:
                logging.error(f"graph=builder event=conflict_with_conditional_edge source={source_id} sink={sink_id}")
                raise EdgeExistsError(source_id, sink_id)

        edge = ConcreteEdge(source, sink)
        self.graph.concrete_edges.append(edge)
        source.outgoing_edges.append(edge)
        sink.incoming_edges.append(edge)
        logging.info(f"graph=builder event=concrete_edge_added source={source_id} sink={sink_id}")

    def add_conditional_edge(self, source_id: str, sink_ids: List[str], router: Callable[[State], str]):
        logging.debug(f"graph=builder event=add_conditional_edge source={source_id} sinks={sink_ids} router={router.__name__}")
        if source_id not in self.graph.nodes:
            raise NodeNotFoundError(source_id)
        if source_id == "end":
            raise GraphConfigurationError("End cannot be the source of a conditional edge")

        source = self.graph.nodes[source_id]
        sinks = []
        for sink_id in sink_ids:
            if sink_id not in self.graph.nodes:
                raise NodeNotFoundError(sink_id)
            if sink_id == "start":
                raise GraphConfigurationError("Start cannot be a sink of conditional edge")
            sinks.append(self.graph.nodes[sink_id])

        for edge in self.graph.concrete_edges:
            if edge.source == source and edge.sink in sinks:
                logging.error(f"graph=builder event=conflict_with_concrete_edge source={source_id} sink={edge.sink.node_id}")
                raise EdgeExistsError(source_id, edge.sink.node_id)

        for cond_edge in self.graph.conditional_edges:
            if cond_edge.source == source:
                for s in sinks:
                    if s in cond_edge.sinks:
                        logging.error(f"graph=builder event=duplicate_conditional_branch source={source_id} sink={s.node_id}")
                        raise EdgeExistsError(source_id, s.node_id)

        edge = ConditionalEdge(source, sinks, router)
        self.graph.conditional_edges.append(edge)
        source.outgoing_edges.append(edge)
        for sink in sinks:
            sink.incoming_edges.append(edge)
        logging.info(f"graph=builder event=conditional_edge_added source={source_id} sinks={[s.node_id for s in sinks]}")

    def build_graph(self) -> Graph:
        logging.debug("graph=builder event=build_graph status=validating")
        start_node = self.graph.start_node
        if any(isinstance(e, ConditionalEdge) for e in start_node.outgoing_edges):
            raise GraphConfigurationError("Start node cannot have a conditional edge")
        if not any(isinstance(e, ConcreteEdge) for e in start_node.outgoing_edges):
            raise GraphConfigurationError("Start node must have at least one outgoing concrete edge")
        if not self.graph.end_node.incoming_edges:
            raise GraphConfigurationError("End node must have at least one incoming edge")
        logging.info("graph=builder event=graph_built status=success")
        return self.graph

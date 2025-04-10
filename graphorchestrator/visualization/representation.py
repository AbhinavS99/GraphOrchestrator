from enum import Enum
from typing import Dict, List

from graphorchestrator.graph.graph import Graph

class RepresentationalEdgeType(Enum):
    CONCRETE = 1
    CONDITIONAL = 2

class RepresentationalNode:
    def __init__(self, node_id: str, node_type: str):
        self.node_id = node_id
        self.node_type = node_type
        self.incoming_edges: List["RepresentationalEdge"] = []
        self.outgoing_edges: List["RepresentationalEdge"] = []

    def __repr__(self) -> str:
        return f"RepresentationalNode(id={self.node_id}, type={self.node_type})"

class RepresentationalEdge:
    def __init__(self, source: RepresentationalNode, sink: RepresentationalNode, edge_type: RepresentationalEdgeType):
        self.source = source
        self.sink = sink
        self.edge_type = edge_type

    def __repr__(self) -> str:
        return f"RepresentationalEdge(source={self.source.node_id}, sink={self.sink.node_id}, type={self.edge_type.name})"

class RepresentationalGraph:
    def __init__(self):
        self.nodes: Dict[str, RepresentationalNode] = {}
        self.edges: List[RepresentationalEdge] = []

    @staticmethod
    def from_graph(graph: Graph) -> "RepresentationalGraph":
        rep_graph = RepresentationalGraph()
        for node_id, node in graph.nodes.items():
            if hasattr(node, "func"):
                node_type = "processing"
            elif node.__class__.__name__ == "AggregatorNode":
                node_type = "aggregator"
            else:
                node_type = "node"
            rep_node = RepresentationalNode(node_id, node_type)
            rep_graph.nodes[node_id] = rep_node

        for edge in graph.concrete_edges:
            src = rep_graph.nodes[edge.source.node_id]
            sink = rep_graph.nodes[edge.sink.node_id]
            rep_edge = RepresentationalEdge(src, sink, RepresentationalEdgeType.CONCRETE)
            rep_graph.edges.append(rep_edge)
            src.outgoing_edges.append(rep_edge)
            sink.incoming_edges.append(rep_edge)

        for cond_edge in graph.conditional_edges:
            src = rep_graph.nodes[cond_edge.source.node_id]
            for sink_node in cond_edge.sinks:
                sink = rep_graph.nodes[sink_node.node_id]
                rep_edge = RepresentationalEdge(src, sink, RepresentationalEdgeType.CONDITIONAL)
                rep_graph.edges.append(rep_edge)
                src.outgoing_edges.append(rep_edge)
                sink.incoming_edges.append(rep_edge)

        return rep_graph

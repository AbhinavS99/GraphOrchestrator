import logging
from typing import Dict, List

from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.concrete import ConcreteEdge
from graphorchestrator.edges.conditional import ConditionalEdge

class Graph:
    def __init__(self, start_node: Node, end_node: Node) -> None:
        self.nodes: Dict[str, Node] = {}
        self.concrete_edges: List[ConcreteEdge] = []
        self.conditional_edges: List[ConditionalEdge] = []
        self.start_node = start_node
        self.end_node = end_node
        logging.info(f"Graph initialized with start node '{start_node.node_id}' and end node '{end_node.node_id}'.")

from typing import Dict, List, Optional

from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.concrete import ConcreteEdge
from graphorchestrator.edges.conditional import ConditionalEdge
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class Graph:
    """
    Represents a directed graph composed of nodes and edges.

    Attributes:
        nodes (Dict[str, Node]): A dictionary mapping node IDs to Node objects.
        concrete_edges (List[ConcreteEdge]): A list of concrete edges in the graph.
        conditional_edges (List[ConditionalEdge]): A list of conditional edges in the graph.
        start_node (Node): The starting node of the graph.
        end_node (Node): The ending node of the graph.
    """

    def __init__(
        self, start_node: Node, end_node: Node, name: Optional[str] = "graph"
    ) -> None:
        """
        Initializes a Graph object.

        Args:
            start_node (Node): The starting node of the graph.
            end_node (Node): The ending node of the graph.
            name (Optional[str]): An optional name for the graph (default: "graph").

        Raises:
            TypeError: If start_node or end_node is not of type Node.

        Returns:
            None
        """
        self.nodes: Dict[str, Node] = {}
        if not isinstance(start_node, Node) or not isinstance(end_node, Node):
            raise TypeError("start_node and end_node must be of type Node")

        self.concrete_edges: List[ConcreteEdge] = []
        self.conditional_edges: List[ConditionalEdge] = []
        self.start_node = start_node
        self.end_node = end_node

        GraphLogger.get().info(
            **wrap_constants(
                message="Graph initialized",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "graph_initialized",
                    LC.CUSTOM: {
                        "start_node_id": start_node.node_id,
                        "end_node_id": end_node.node_id,
                    },
                }
            )
        )

from typing import Dict, List, Optional

from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.concrete import ConcreteEdge
from graphorchestrator.edges.conditional import ConditionalEdge
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class Graph:
    def __init__(
        self, start_node: Node, end_node: Node, name: Optional[str] = "graph"
    ) -> None:
        self.nodes: Dict[str, Node] = {}
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

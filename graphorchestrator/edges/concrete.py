from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge

from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class ConcreteEdge(Edge):
    """
    Concrete implementation of an edge in a graph.

    This class represents a direct connection between a source node and a sink node
    in the graph. It logs the creation of the edge for debugging purposes.

    Attributes:
        source (Node): The source node of the edge.
        sink (Node): The sink node of the edge.
    """

    def __init__(self, source: Node, sink: Node) -> None:
        self.source = source
        self.sink = sink

        GraphLogger.get().info(
            **wrap_constants(
                message="Concrete edge created",
                **{
                    LC.EVENT_TYPE: "edge",
                    LC.ACTION: "edge_created",
                    LC.EDGE_TYPE: "concrete",
                    LC.SOURCE_NODE: self.source.node_id,
                    LC.SINK_NODE: self.sink.node_id,
                }
            )
        )

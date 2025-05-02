from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge

from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class ConcreteEdge(Edge):
    """Concrete implementation of an edge in a graph.

    This class represents a direct, unconditional connection between
    a source node and a sink node in the graph.
    It logs the creation of the edge for debugging and monitoring purposes.

    Attributes:
        source (Node): The source node of the edge.
        sink (Node): The sink node of the edge.
    """

    def __init__(self, source: Node, sink: Node):
        """Initializes a ConcreteEdge object.

        This method sets up the connection between a source node and
        a sink node, and logs the creation of this edge.

        Args:
            source (Node): The source node of the edge.
            sink (Node): The sink node of the edge.
        """
        self.source = source
        # Sets the source node of the edge.
        self.sink = sink
        # Sets the sink node of the edge.

        GraphLogger.get().info(
            # Logs the creation of the edge with relevant details.
            **wrap_constants(
                # Wraps the log message with necessary constants.
                message="Concrete edge created",
                **{
                    # Additional details for the log message.
                    LC.EVENT_TYPE: "edge",
                    LC.ACTION: "edge_created",
                    LC.EDGE_TYPE: "concrete",
                    LC.SOURCE_NODE: self.source.node_id,
                    LC.SINK_NODE: self.sink.node_id,
                }
            )
        )

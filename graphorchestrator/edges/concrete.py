from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge

from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class ConcreteEdge(Edge):
    """
    Represents a direct, unconditional connection between two nodes in the graph.

    This edge always passes execution from the source node to the sink node without
    evaluating any condition. It is suitable for simple linear flows.

    Attributes
    ----------
    `source` : `Node`
        The source node where the edge originates.
    `sink` : `Node`
        The sink node where the edge terminates.

    Examples
    --------
    ```python
    edge = ConcreteEdge(source=node_a, sink=node_b)
    ```
    """

    def __init__(self, source: Node, sink: Node):
        """
        Initializes a `ConcreteEdge` between a given source and sink node.

        Parameters
        ----------
        `source` : `Node`
            The starting node of the edge.
        `sink` : `Node`
            The destination node of the edge.
        """
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

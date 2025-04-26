import logging
from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge


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
        logging.info(
            f"edge=concrete event=init source={self.source.node_id} sink={self.sink.node_id}"
        )

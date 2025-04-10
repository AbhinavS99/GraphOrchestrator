import logging
from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge

class ConcreteEdge(Edge):
    def __init__(self, source: Node, sink: Node) -> None:
        self.source = source
        self.sink = sink
        logging.info(
            f"edge=concrete event=init source={self.source.node_id} sink={self.sink.node_id}"
        )

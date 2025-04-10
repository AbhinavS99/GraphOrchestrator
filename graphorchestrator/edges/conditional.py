import logging
from typing import Callable, List

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import RoutingFunctionNotDecoratedError
from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge

class ConditionalEdge(Edge):
    def __init__(self, source: Node, sinks: List[Node], router: Callable[[State], str]) -> None:
        self.source = source
        self.sinks = sinks
        if not getattr(router, "is_routing_function", False):
            raise RoutingFunctionNotDecoratedError(router)
        self.routing_function = router

        sink_ids = ",".join([s.node_id for s in sinks])
        logging.info(
            f"edge=conditional event=init source={self.source.node_id} sinks=[{sink_ids}] router={router.__name__}"
        )

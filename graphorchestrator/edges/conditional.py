import logging
from typing import Callable, List

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import RoutingFunctionNotDecoratedError
from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge


class ConditionalEdge(Edge):
    """
    Represents a conditional edge in a graph.

    A ConditionalEdge directs the flow of execution to one of several sink nodes
    based on the result of a routing function.

    Args:
        source (Node): The source node of the edge.
        sinks (List[Node]): A list of possible sink nodes for the edge.
        router (Callable[[State], str]): A routing function that determines
            which sink node to direct to based on the current state.

    Raises:
        RoutingFunctionNotDecoratedError: If the provided router function
            is not decorated with @routing_function.
    """

    def __init__(
        self, source: Node, sinks: List[Node], router: Callable[[State], str]
    ) -> None:
        """Initializes a ConditionalEdge with a source, multiple sinks, and a router function."""
        self.source = source
        self.sinks = sinks
        if not getattr(router, "is_routing_function", False):
            raise RoutingFunctionNotDecoratedError(router)
        self.routing_function = router

        sink_ids = ",".join([s.node_id for s in sinks])  # type: ignore
        logging.info(
            f"edge=conditional event=init source={self.source.node_id} sinks=[{sink_ids}] router={router.__name__}"
        )

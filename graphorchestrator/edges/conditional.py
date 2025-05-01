from typing import Callable, List

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import RoutingFunctionNotDecoratedError
from graphorchestrator.nodes.base import Node
from graphorchestrator.edges.base import Edge

from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class ConditionalEdge(Edge):
    """
    Represents a conditional edge in a graph.

    A ConditionalEdge directs the flow of execution to one of several sink nodes
    based on the result of a routing function.
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
        sink_ids = [s.node_id for s in sinks]

        GraphLogger.get().info(
            **wrap_constants(
                message="Conditional edge created",
                **{
                    LC.EVENT_TYPE: "edge",
                    LC.ACTION: "edge_created",
                    LC.EDGE_TYPE: "conditional",
                    LC.SOURCE_NODE: self.source.node_id,
                    LC.SINK_NODE: sink_ids,  # Using SINK_NODE for consistency; optional to split as LC.SINK_NODES
                    LC.ROUTER_FUNC: router.__name__,
                }
            )
        )

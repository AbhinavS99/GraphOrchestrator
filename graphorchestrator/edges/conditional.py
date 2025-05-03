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

    A `ConditionalEdge` enables dynamic routing of execution from a source node to
    one of several sink nodes based on a routing function. This function evaluates the
    current execution `State` and determines the next node by returning a matching node ID.

    Attributes
    ----------
    `source` : `Node`
        The node from which the edge originates.
    `sinks` : `List[Node]`
        A list of potential destination nodes.
    `routing_function` : `Callable[[State], str]`
        A function that evaluates the state and returns the ID of the next node.

    Examples
    --------
    ```python
    @routing_function
    def router(state: State) -> str:
        return "approve" if state.is_valid() else "reject"

    edge = ConditionalEdge(source=node_a, sinks=[approve_node, reject_node], router=router)
    ```
    """

    def __init__(
        self, source: Node, sinks: List[Node], router: Callable[[State], str]
    ) -> None:
        """
        Initializes a `ConditionalEdge` between a source node and multiple sink nodes.

        Parameters
        ----------
        `source` : `Node`
            The starting point of the edge.
        `sinks` : `List[Node]`
            The list of possible destination nodes.
        `router` : `Callable[[State], str]`
            A function that returns the node ID of the next step based on the given state.

        Raises
        ------
        `RoutingFunctionNotDecoratedError`
            If the provided routing function is not decorated with `@routing_function`.
        """
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
                    LC.SINK_NODE: sink_ids,
                    LC.ROUTER_FUNC: router.__name__,
                }
            )
        )

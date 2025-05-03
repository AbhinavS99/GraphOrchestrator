from abc import ABC, abstractmethod
from typing import Optional

from graphorchestrator.core.state import State
from graphorchestrator.core.retry import RetryPolicy
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class Node(ABC):
    """
    Abstract base class representing a node in a graph.

    Nodes have unique IDs and can have incoming and outgoing edges.
    """

    def __init__(self, node_id: str) -> None:
        """
        Initializes a new Node instance.

        Args:
            node_id (str): The unique identifier for this node.
        """
        self.node_id: str = node_id
        self.incoming_edges = []
        self.outgoing_edges = []
        self.fallback_node_id: Optional[str] = None
        self.retry_policy: Optional[RetryPolicy] = None

        GraphLogger.get().info(
            **wrap_constants(
                message="Node initialized",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: self.__class__.__name__,
                    LC.ACTION: "node_created",
                    LC.CUSTOM: {
                        "incoming_edges": 0,
                        "outgoing_edges": 0,
                        "fallback_node_id": None,
                        "retry_policy": None,
                    },
                }
            )
        )

    @abstractmethod
    def execute(self, state: State):
        """
        Abstract method to execute the node's logic.

        Args:
            state: The current state of the execution.
        """
        raise NotImplementedError

    def set_fallback(self, fallback_node_id: str) -> None:
        """
        Sets the fallback node ID for this node.

        Args:
            fallback_node_id (str): The ID of the fallback node.
        """
        self.fallback_node_id = fallback_node_id

    def set_retry_policy(self, retry_policy: RetryPolicy) -> None:
        """
        Sets the retry policy for this node.

        Args:
            retry_policy (RetryPolicy): The retry policy to apply.
        """
        self.retry_policy = retry_policy

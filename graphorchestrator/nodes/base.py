import logging
from abc import ABC, abstractmethod

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
        
        # Log the initialization of the node
        logging.info(
            f"node=base event=init node_id={self.node_id} incoming=0 outgoing=0"
        )

    @abstractmethod
    def execute(self, state):
        """
        Abstract method to execute the node's logic.

        Args:
            state: The current state of the execution.
        """
        raise NotImplementedError

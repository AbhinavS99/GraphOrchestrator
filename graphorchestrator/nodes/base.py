import logging
from abc import ABC, abstractmethod

class Node(ABC):
    def __init__(self, node_id: str) -> None:
        self.node_id: str = node_id
        self.incoming_edges = []
        self.outgoing_edges = []
        logging.info(
            f"node=base event=init node_id={self.node_id} incoming=0 outgoing=0"
        )

    @abstractmethod
    def execute(self, state):
        pass

import pickle
from typing import Dict, List, Optional
from graphorchestrator.core.state import State
from graphorchestrator.graph.graph import Graph
from graphorchestrator.core.retry import RetryPolicy


class CheckpointData:
    def __init__(
        self,
        graph: Graph,
        initial_state: State,
        active_states: Dict[str, List[State]],
        superstep: int,
        final_state: Optional[State],
        retry_policy: RetryPolicy,
        max_workers: int,
    ):
        self.graph = graph
        self.initial_state = initial_state
        self.active_states = active_states
        self.superstep = superstep
        self.final_state = final_state
        self.retry_policy = retry_policy
        self.max_workers = max_workers

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "CheckpointData":
        with open(path, "rb") as f:
            return pickle.load(f)

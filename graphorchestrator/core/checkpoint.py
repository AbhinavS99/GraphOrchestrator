import pickle
from typing import Dict, List, Optional

from graphorchestrator.core.state import State
from graphorchestrator.graph.graph import Graph
from graphorchestrator.core.retry import RetryPolicy

from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


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
        log = GraphLogger.get()
        with open(path, "wb") as f:
            pickle.dump(self, f)

        log.info(
            **wrap_constants(
                message="Checkpoint saved to disk",
                level="INFO",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "checkpoint_save",
                    LC.SUPERSTEP: self.superstep,
                    LC.CUSTOM: {
                        "path": path,
                        "final_state_message_count": (
                            len(self.final_state.messages) if self.final_state else None
                        ),
                        "active_nodes": list(self.active_states.keys()),
                    },
                }
            )
        )

    @staticmethod
    def load(path: str) -> "CheckpointData":
        log = GraphLogger.get()
        with open(path, "rb") as f:
            data: CheckpointData = pickle.load(f)

        log.info(
            **wrap_constants(
                message="Checkpoint loaded from disk",
                level="INFO",
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "checkpoint_load",
                    LC.SUPERSTEP: data.superstep,
                    LC.CUSTOM: {
                        "path": path,
                        "active_nodes": list(data.active_states.keys()),
                    },
                }
            )
        )
        return data

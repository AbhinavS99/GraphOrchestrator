# Import necessary modules for serialization, type hinting, and graph operations.
import pickle
from typing import Dict, List, Optional

# Import custom classes and modules from the graphorchestrator package.
from graphorchestrator.core.state import State
from graphorchestrator.graph.graph import Graph
from graphorchestrator.core.retry import RetryPolicy
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class CheckpointData:
    """Represents the data to be checkpointed, including graph state, and execution metadata."""

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
        """
        Initializes the CheckpointData with the necessary components for checkpointing.

        Args:
            graph (Graph): The graph structure.
            initial_state (State): The initial state of the graph execution.
            active_states (Dict[str, List[State]]): The states of active nodes.
            superstep (int): The current superstep number.
            final_state (Optional[State]): The final state of the graph execution, if available.
            retry_policy (RetryPolicy): The retry policy applied to the graph execution.
            max_workers (int): The maximum number of workers used in execution.
        """

        # Assign the provided parameters to the object's attributes.
        self.graph = graph
        self.initial_state = initial_state
        self.active_states = active_states
        self.superstep = superstep
        self.final_state = final_state
        self.retry_policy = retry_policy
        self.max_workers = max_workers

    def save(self, path: str) -> None:
        """
        Serializes and saves the checkpoint data to the specified path.

        Args:
            path (str): The file path where the checkpoint will be saved.
        """

        # Get the graph logger instance.
        log = GraphLogger.get()

        # Serialize the checkpoint data and save it to the specified file path.
        with open(path, "wb") as f:
            pickle.dump(self, f)

        log.info(
            **wrap_constants(
                message="Checkpoint saved to disk",
                level="INFO",
                # Prepare log entry with essential checkpointing information.
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
        """
        Loads checkpoint data from the specified path.

        Args:
            path (str): The file path from which to load the checkpoint.

        Returns:
            CheckpointData: The loaded checkpoint data.
        """
        # Get the graph logger instance.
        log = GraphLogger.get()
        # Deserialize the checkpoint data from the specified file path.
        with open(path, "rb") as f:
            data: CheckpointData = pickle.load(f)

        log.info(
            **wrap_constants(
                message="Checkpoint loaded from disk",
                level="INFO",
                # Prepare log entry with essential checkpoint loading information.
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
        # Return the loaded checkpoint data.
        return data

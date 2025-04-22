import os
import pickle
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, List
from graphorchestrator.core.state import State

class CheckpointStore(ABC):
    @abstractmethod
    def save_checkpoint(self, step: int, active_states: Dict[str, List[State]]):
        raise NotImplementedError
    
    @abstractmethod
    def load_checkpoint(self) -> Optional[Tuple[int, Dict[str, List[State]]]]:
        raise NotImplementedError
    
    @abstractmethod
    def clear_checkpoints(self):
        raise NotImplementedError


class PickleCheckpointStore(CheckpointStore):
    def __init__(self, path: str = ".checkpoints/graph.pkl"):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def save_checkpoint(self, step: int, active_states: Dict[str, List[State]]):
        with open(self.path, "wb") as f:
            pickle.dump((step, active_states), f)

    def load_checkpoint(self) -> Optional[Tuple[int, Dict[str, List[State]]]]:
        if not os.path.exists(self.path):
            return None
        with open(self.path, "rb") as f:
            return pickle.load(f)

    def clear_checkpoints(self):
        if os.path.exists(self.path):
            os.remove(self.path)
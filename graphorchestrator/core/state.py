from dataclasses import dataclass, field
from typing import Any, List

@dataclass
class State:
    messages: List[Any] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"State({self.messages})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, State):
            return NotImplemented
        return self.messages == other.messages
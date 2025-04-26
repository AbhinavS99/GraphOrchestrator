from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class State:
    """
    Represents the state of a process or workflow, maintaining a list of messages.

    Attributes:
        messages (List[Any]): A list to store messages related to the state.
    """

    messages: List[Any] = field(default_factory=list)

    def __repr__(self) -> str:
        """
        Provides a string representation of the State object.

        Returns:
            str: A string representation of the State, including its messages.
        """
        return f"State({self.messages})"

    def __eq__(self, other: Any) -> bool:
        """
        Checks if the current State object is equal to another object.

        Args:
            other (Any): The object to compare with.

        Returns:
            bool: True if the objects are equal, False otherwise.
        """
        if not isinstance(other, State):
            return NotImplemented
        return self.messages == other.messages

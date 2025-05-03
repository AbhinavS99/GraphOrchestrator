from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class State:
    """
    Represents the execution state passed between nodes in a workflow graph.

    The `State` object holds a list of messages that carry intermediate data,
    outputs, or contextual information through the graph. It is the core data
    container in GraphOrchestrator's node-based execution model.

    Attributes
    ----------
    `messages` : `List[Any]`
        A list of message objects—typically strings, dictionaries, or structured data—
        representing the current state at a given point in the workflow.

    Examples
    --------
    Create a new state:

    ```python
    s = State(messages=["step-1 started"])
    print(s)  # Output: State(['step-1 started'])
    ```

    Compare two states:

    ```python
    State(["a", "b"]) == State(["a", "b"])  # True
    ```

    Append a message and inspect the state:

    ```python
    s.messages.append("step-1 completed")
    print(s)
    # Output: State(['step-1 started', 'step-1 completed'])
    ```
    """

    messages: List[Any] = field(default_factory=list)

    def __repr__(self) -> str:
        """
        Returns a developer-friendly string representation of the state.

        Returns
        -------
        `str`
            A string in the format `State([...])`, showing the internal message list.
        """
        return f"State({self.messages})"

    def __eq__(self, other: Any) -> bool:
        """
        Compares two `State` objects for equality based on their message content.

        Parameters
        ----------
        `other` : `Any`
            The object to compare against.

        Returns
        -------
        `bool`
            `True` if the other object is a `State` instance with identical messages;
            `False` otherwise.
        """
        if not isinstance(other, State):
            return NotImplemented
        return self.messages == other.messages

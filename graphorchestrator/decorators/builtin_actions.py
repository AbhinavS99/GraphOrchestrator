import random
from typing import List

from graphorchestrator.core.state import State
from graphorchestrator.decorators.actions import node_action, aggregator_action


@node_action
def passThrough(state: State) -> State:
    """
    A node action that simply passes the state through unchanged.

    Args:
        state (State): The input state.

    Returns:
        State: The same state as the input.
    """
    return state


@aggregator_action
def selectRandomState(states: List[State]) -> State:
    """
    An aggregator action that selects a random state from a list of states.

    Args:
        states (List[State]): A list of states.

    Returns:
        State: A randomly selected state from the input list.
    """
    return random.choice(states)

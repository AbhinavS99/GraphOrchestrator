import random
from typing import List

from graphorchestrator.core.state import State
from graphorchestrator.decorators.actions import node_action, aggregator_action

@node_action
def passThrough(state: State) -> State:
    return state

@aggregator_action
def selectRandomState(states: List[State]) -> State:
    return random.choice(states)
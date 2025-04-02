import logging
import random
import copy
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import concurrent.futures
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from collections import deque, defaultdict
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle

# ----------------------------------------------------------------------
# Logging Configuration
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Thread: %(threadName)s] %(message)s"
)

# ----------------------------------------------------------------------
# Custom Exceptions
# ----------------------------------------------------------------------
class GraphOrchestratorException(Exception):
    """Base class for graph orchestration exceptions."""
    pass

class DuplicateNodeError(GraphOrchestratorException):
    def __init__(self, node_id: str):
        super().__init__(f"Node with id '{node_id}' already exists.")
        self.node_id = node_id

class EdgeExistsError(GraphOrchestratorException):
    def __init__(self, source_id: str, sink_id: str):
        super().__init__(f"Edge from '{source_id}' to '{sink_id}' already exists.")
        self.source_id = source_id
        self.sink_id = sink_id

class NodeNotFoundError(GraphOrchestratorException):
    def __init__(self, node_id: str):
        super().__init__(f"Node '{node_id}' not found in the graph.")
        self.node_id = node_id

class GraphConfigurationError(GraphOrchestratorException):
    def __init__(self, message: str):
        super().__init__(f"Graph configuration error: {message}")

class GraphExecutionError(GraphOrchestratorException):
    def __init__(self, node_id: str, message: str):
        super().__init__(f"Execution failed at node '{node_id}': {message}")
        self.node_id = node_id
        self.message = message

class InvalidRoutingFunctionOutput(GraphOrchestratorException):
    def __init__(self, returned_value: Any):
        super().__init__(f"Routing function must return a string, but got {type(returned_value).__name__}: {returned_value}")
        self.returned_value = returned_value

class InvalideNodeActionOutput(GraphOrchestratorException):
    def __init__(self, returned_value: Any):
        super().__init__(f"Node action must return a state, but got {type(returned_value).__name__}: {returned_value}")
        self.returned_value = returned_value

class InvalidToolMehtodOutput(GraphOrchestratorException):
    def __init__(self, returned_value: Any):
        super().__init__(f"Tool method must return a state, but got {type(returned_value).__name__}: {returned_value}")
        self.returned_value = returned_value

class NodeActionNotDecoratedError(GraphOrchestratorException):
    def __init__(self, func: Callable):
        func_name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{func_name}' passed to ProcessingNode must be decorated with @node_action.")

class RoutingFunctionNotDecoratedError(GraphOrchestratorException):
    def __init__(self, func: Callable):
        func_name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{func_name}' passed to ConditionalEdge must be decorated with @routing_function.")

class InvalidAggregatorActionError(GraphOrchestratorException):
    def __init__(self, returned_value: Any):
        super().__init__(f"Aggregator action must return a state, but got {type(returned_value).__name__}")
        self.returned_value = returned_value

class AggregatorActionNotDecorated(GraphOrchestratorException):
    def __init__(self, func: Callable):
        func_name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{func_name}' passed to Aggregator must be decorated with @aggregator_action")

class EmptyToolNodeDescriptionError(GraphOrchestratorException):
    def __init__(self, func: Callable):
        func_name = getattr(func, '__name__', repr(func))
        super().__init__(f"The tool function '{func_name}' has no description or docstring provided")

class ToolMethodNotDecorated(GraphOrchestratorException):
    def __init__(self, func: Callable):
        func_name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{func_name}' passed to ToolNode has to be decorted with @tool_method")

# ----------------------------------------------------------------------
# Retry Policy Class
# ----------------------------------------------------------------------
@dataclass
class RetryPolicy:
    max_retries: int = 3       # maximum number of retries
    delay: float = 1.0         # initial delay in seconds
    backoff: float = 2.0       # factor by which the delay is multiplied on each retry

# ----------------------------------------------------------------------
# State Class
# ----------------------------------------------------------------------
@dataclass
class State:
    messages: List[Any] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"State({self.messages})"
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, State):
            return NotImplemented
        return self.messages == other.messages

# ----------------------------------------------------------------------
# Decorators
# ----------------------------------------------------------------------
def routing_function(func: Callable[[State], str]) -> Callable[[State], str]:
    """
    Decorator to ensure a routing function returns a single string.
    """
    @wraps(func)
    def wrapper(state: State) -> str:
        logging.info(f"Routing function '{func.__name__}' invoked with state: {state}")
        result = func(state)
        if not isinstance(result, str):
            logging.error(f"Routing function '{func.__name__}' returned a non-string value: {result}")
            raise InvalidRoutingFunctionOutput(result)
        logging.info(f"Routing function '{func.__name__}' returned '{result}' for state: {state}")
        return result
    wrapper.is_routing_function = True
    return wrapper

def node_action(func: Callable[[State], State]) -> Callable[[State], State]:
    """
    Decorator to mark a function as a valid node action.
    """
    @wraps(func)
    def wrapper(state: State) -> State:
        logging.info(f"Node action '{func.__name__}' invoked with state: {state}")
        result = func(state)
        if not isinstance(result, State):
            logging.error(f"Node action '{func.__name__}' returned a non-state value: {result}")
            raise InvalideNodeActionOutput(result)
        return state
    wrapper.is_node_action = True
    return wrapper

def tool_method(func: Callable[[State], State]) -> Callable[[State], State]:
    """
    Decorator to mark a function as valid tool method.
    """
    @wraps(func)
    def wrapper(state: State) -> State:
        logging.info(f"Tool method '{func.__name__}' invoked with state: {state}")
        result = func(state)
        if not isinstance(result, State):
            logging.error(f"Tool method '{func.__name__}' returned a non-state value: {result}")
            raise InvalidToolMehtodOutput(result)
        return state
    wrapper.is_node_action = True
    wrapper.is_tool_method = True
    return wrapper

def aggregator_action(func: Callable[[List[State]], State]) -> Callable[[List[State]], State]:
    """
    Decorator to mark a function as a valid aggregator action
    """
    @wraps(func)
    def wrapper(states: List[State]) -> State:
        logging.info(f"Aggregator action '{func.__name__}' invoked with state: {states}")
        result = func(states)
        if not isinstance(result, State):
            logging.error(f"Aggregator action '{func.__name__}' returned a non-state value: {result}")
            raise InvalidAggregatorActionError(result)
        logging.info(f"Routing function '{func.__name__}' returned '{result}'")
        return result
    wrapper.is_aggregator_action = True
    return wrapper    


# ----------------------------------------------------------------------
# Pass Through - function decorated to pass the state unchanged
# ----------------------------------------------------------------------
@node_action
def passThrough(state):
    return state

# ----------------------------------------------------------------------
# Select Random State - function decorated to select any random state 
# ----------------------------------------------------------------------
@aggregator_action
def selectRandomState(states):
    return random.choice(states)

# ----------------------------------------------------------------------
# Node Classes
# ----------------------------------------------------------------------
class Node(ABC):
    def __init__(self, node_id: str) -> None:
        self.node_id: str = node_id
        self.incoming_edges: List["Edge"] = []
        self.outgoing_edges: List["Edge"] = []
        logging.info(f"Initialized node '{self.node_id}'.")

    @abstractmethod
    def execute(self, state: Any) -> Any:
        """Executes the node's function with the provided state."""
        pass

class ProcessingNode(Node):
    def __init__(self, node_id: str, func: Callable[[State], State]) -> None:
        super().__init__(node_id)
        self.func: Callable[[State], State] = func
        func_name = getattr(func, '__name__', func.__class__.__name__)
        if not getattr(func, "is_node_action", False):
            raise NodeActionNotDecoratedError(func)
        logging.info(f"ProcessingNode '{self.node_id}' created with processing function '{func.__name__}'.")

    def execute(self, state: State) -> State:
        logging.info(f"ProcessingNode '{self.node_id}' starting execution with input: {state}")
        result = self.func(state)
        logging.info(f"ProcessingNode '{self.node_id}' finished execution with output: {result}")
        return result

class AggregatorNode(Node):
    def __init__(self, node_id: str, aggregator_action: Callable[[List[State]], State]) -> None:
        super().__init__(node_id)
        self.aggregator_action: Callable[[List[State]], State] = aggregator_action
        if not getattr(aggregator_action, "is_aggregator_action", False):
            raise AggregatorActionNotDecorated(aggregator_action)
        logging.info(f"AggregatorNode '{self.node_id}' created.")

    def execute(self, states: List[State]) -> State:
        logging.info(f"AggregatorNode '{self.node_id}' starting aggregation of {len(states)} states.")
        result = self.aggregator_action(states)
        logging.info(f"AggregatorNode '{self.node_id}' completed aggregation with result: {result}")
        return result

class ToolNode(ProcessingNode):
    def __init__(self, node_id: str, tool_method: Callable[[State], State], description: Optional[str]) -> None:
        method_docstring = tool_method.__doc__
        if (method_docstring == None or method_docstring.strip() == "") and (description == None or description.strip() == ""):
            raise EmptyToolNodeDescriptionError(tool_method)
        if not getattr(tool_method, "is_tool_method", False):
            raise ToolMethodNotDecorated(tool_method)
        super().__init__(node_id, tool_method)
        logging.info(f"ToolNode '{self.node_id}' created with tool method '{tool_method.__name__}.'")
    
    def execute(self, state: State) -> State:
        logging.info(f"ToolNode '{self.node_id}' starting execution with input: {state}")
        result = self.func(state)
        logging.info(f"ToolNode '{self.node_id}' finished execution with output: {result}")
        return result

# ----------------------------------------------------------------------
# Edge Classes
# ----------------------------------------------------------------------
class Edge(ABC):
    """Base class for graph edges."""
    pass

class ConcreteEdge(Edge):
    def __init__(self, source: Node, sink: Node) -> None:
        self.source: Node = source
        self.sink: Node = sink
        logging.info(f"ConcreteEdge created from '{source.node_id}' to '{sink.node_id}'.")

class ConditionalEdge(Edge):
    def __init__(self, source: Node, sinks: List[Node], router: Callable[[State], str]) -> None:
        self.source: Node = source
        self.sinks: List[Node] = sinks
        if not getattr(router, "is_routing_function", False):
            raise RoutingFunctionNotDecoratedError(router)
        self.routing_function: Callable[[State], str] = router
        logging.info(f"ConditionalEdge created from '{source.node_id}' to {[sink.node_id for sink in sinks]} using router '{router.__name__}'.")

# ----------------------------------------------------------------------
# Graph Class
# ----------------------------------------------------------------------
class Graph:
    def __init__(self, start_node: Node, end_node: Node) -> None:
        self.nodes: Dict[str, Node] = {}
        self.concrete_edges: List[ConcreteEdge] = []
        self.conditional_edges: List[ConditionalEdge] = []
        self.start_node: Node = start_node
        self.end_node: Node = end_node
        logging.info(f"Graph initialized with start node '{start_node.node_id}' and end node '{end_node.node_id}'.")

# ----------------------------------------------------------------------
# GraphBuilder Class
# ----------------------------------------------------------------------
class GraphBuilder:
    def __init__(self) -> None:
        logging.info("Initializing GraphBuilder...")
        start_node = ProcessingNode("start", passThrough)
        end_node = ProcessingNode("end", passThrough)
        self.graph: Graph = Graph(start_node, end_node)
        # Add predefined start and end nodes
        self.add_node(start_node)
        self.add_node(end_node)
        logging.info(f"GraphBuilder initialized with nodes: {list(self.graph.nodes.keys())}.")

    def add_node(self, node: Node) -> None:
        logging.info(f"Attempting to add node '{node.node_id}' to graph...")
        if node.node_id in self.graph.nodes:
            logging.error(f"Duplicate node detected: '{node.node_id}'.")
            raise DuplicateNodeError(node.node_id)
        self.graph.nodes[node.node_id] = node
        logging.info(f"Node '{node.node_id}' added successfully. Current nodes: {list(self.graph.nodes.keys())}.")

    def add_aggregator(self, aggregator: AggregatorNode) -> None:
        logging.info(f"Attempting to add aggregator node '{aggregator.node_id}'...")
        if aggregator.node_id in self.graph.nodes:
            logging.error(f"Duplicate aggregator node detected: '{aggregator.node_id}'.")
            raise DuplicateNodeError(aggregator.node_id)
        self.graph.nodes[aggregator.node_id] = aggregator
        logging.info(f"Aggregator node '{aggregator.node_id}' added successfully.")

    def add_concrete_edge(self, source_id: str, sink_id: str) -> None:
        logging.info(f"Attempting to add concrete edge from '{source_id}' to '{sink_id}'...")
        if source_id not in self.graph.nodes:
            logging.error(f"Source node '{source_id}' not found.")
            raise NodeNotFoundError(source_id)
        if source_id == "end":
            logging.error("End cannot be the source of a concrete edge")
            raise GraphConfigurationError("End cannot be the source of a concrete edge")
        if sink_id not in self.graph.nodes:
            logging.error(f"Sink node '{sink_id}' not found.")
            raise NodeNotFoundError(sink_id)
        if sink_id == "start":
            logging.error("Start node cannot be a sink of concrete edge.")
            raise GraphConfigurationError("Start node cannot be a sink of concrete edge.")
        source = self.graph.nodes[source_id]
        sink = self.graph.nodes[sink_id]
        # Check for existing concrete edge.
        for edge in self.graph.concrete_edges:
            if edge.source == source and edge.sink == sink:
                logging.error(f"Duplicate concrete edge exists from '{source_id}' to '{sink_id}'.")
                raise EdgeExistsError(source_id, sink_id)
        # Also check if a conditional edge branch exists between these nodes.
        for cond_edge in self.graph.conditional_edges:
            if cond_edge.source == source and sink in cond_edge.sinks:
                logging.error(f"Conditional edge branch already exists from '{source_id}' to '{sink_id}'.")
                raise EdgeExistsError(source_id, sink_id)
        edge = ConcreteEdge(source, sink)
        self.graph.concrete_edges.append(edge)
        source.outgoing_edges.append(edge)
        sink.incoming_edges.append(edge)
        logging.info(f"Concrete edge added successfully from '{source_id}' to '{sink_id}'.")

    def add_conditional_edge(self, source_id: str, sink_ids: List[str], routing_function: Callable[[State], str]) -> None:
        logging.info(f"Attempting to add conditional edge from '{source_id}' to sinks: {sink_ids} using routing function '{routing_function.__name__}'...")
        if source_id not in self.graph.nodes:
            logging.error(f"Source node '{source_id}' not found for conditional edge.")
            raise NodeNotFoundError(source_id)
        if source_id == "end":
            logging.error("End cannot be the source of a conditional edge")
            raise GraphConfigurationError("End cannot be the source of a conditional edge")
        source = self.graph.nodes[source_id]
        sinks: List[Node] = []
        for sink_id in sink_ids:
            if sink_id not in self.graph.nodes:
                logging.error(f"Sink node '{sink_id}' not found for conditional edge.")
                raise NodeNotFoundError(sink_id)
            if sink_id == "start":
                logging.error("Start node cannot be a sink of conditional edge.")
                raise GraphConfigurationError("Start node cannot be a sink of conditional edge.")
            sinks.append(self.graph.nodes[sink_id])
        # Check for duplicate edges in concrete edges.
        for edge in self.graph.concrete_edges:
            if edge.source == source and edge.sink in sinks:
                logging.error(f"Concrete edge exists from '{source_id}' to '{edge.sink.node_id}', cannot add conditional edge.")
                raise EdgeExistsError(source_id, edge.sink.node_id)
        # Check for duplicate conditional edges.
        for cond_edge in self.graph.conditional_edges:
            if cond_edge.source == source:
                for s in sinks:
                    if s in cond_edge.sinks:
                        logging.error(f"Conditional edge branch already exists from '{source_id}' to '{s.node_id}'.")
                        raise EdgeExistsError(source_id, s.node_id)
        edge = ConditionalEdge(source, sinks, routing_function)
        self.graph.conditional_edges.append(edge)
        source.outgoing_edges.append(edge)
        for sink in sinks:
            sink.incoming_edges.append(edge)
        logging.info(f"Conditional edge added successfully from '{source_id}' to {[sink.node_id for sink in sinks]}.")

    def build_graph(self) -> Graph:
        logging.info("Starting graph validation and build process...")
        # Validate start node: no conditional edges and at least one concrete edge.
        start_node = self.graph.start_node
        for edge in start_node.outgoing_edges:
            if isinstance(edge, ConditionalEdge):
                logging.error("Validation failed: Start node has a conditional edge.")
                raise GraphConfigurationError("Start node cannot have a conditional edge.")
        if not any(isinstance(edge, ConcreteEdge) for edge in start_node.outgoing_edges):
            logging.error("Validation failed: Start node does not have any outgoing concrete edge.")
            raise GraphConfigurationError("Start node must have at least one outgoing concrete edge.")
        # Validate end node: must have at least one incoming edge.
        end_node = self.graph.end_node
        if not end_node.incoming_edges:
            logging.error("Validation failed: End node does not have any incoming edge.")
            raise GraphConfigurationError("End node must have at least one incoming edge.")
        logging.info("Graph validated and built successfully.")
        return self.graph

# ----------------------------------------------------------------------
# GraphExecutor Class
# ----------------------------------------------------------------------
class GraphExecutor:
    def __init__(self, graph: Graph, initial_state: State, max_workers: int = 4, retry_policy: Optional[RetryPolicy] = None) -> None:
        logging.info("Initializing GraphExecutor...")
        self.graph: Graph = graph
        self.initial_state: State = initial_state
        self.max_workers: int = max_workers
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)
        # Map node_id to list of states pending execution.
        self.active_states: Dict[str, List[State]] = defaultdict(list)
        self.active_states[graph.start_node.node_id].append(initial_state)
        self.retry_policy: RetryPolicy = retry_policy if retry_policy is not None else RetryPolicy()
        logging.info(f"GraphExecutor initialized. Starting at node '{graph.start_node.node_id}' with initial state: {initial_state}")

    def execute_node_with_retry(self, node: Node, input_data: Any, retry_policy: RetryPolicy) -> Any:
        attempt = 0
        current_delay = retry_policy.delay
        while attempt <= retry_policy.max_retries:
            try:
                return node.execute(input_data)
            except Exception as e:
                if attempt == retry_policy.max_retries:
                    logging.error(f"Node '{node.node_id}' failed after {attempt + 1} attempts: {e}")
                    raise e
                logging.warning(f"Node '{node.node_id}' execution failed on attempt {attempt + 1} with error: {e}. Retrying in {current_delay} seconds...")
                time.sleep(current_delay)
                current_delay *= retry_policy.backoff
                attempt += 1

    def execute(self, max_supersteps: int = 100, superstep_timeout: float = 300.0) -> Optional[State]:
        logging.info("Beginning graph execution...")
        superstep: int = 0
        final_state: Optional[State] = None

        while self.active_states and superstep < max_supersteps:
            logging.info(f"\n=== Superstep {superstep} ===")
            logging.info(f"Active nodes for execution: {list(self.active_states.keys())}")
            next_active_states: Dict[str, List[State]] = defaultdict(list)
            futures: List[tuple[str, Any]] = []

            # Submit execution for each active node.
            for node_id, states in self.active_states.items():
                node = self.graph.nodes[node_id]
                logging.info(f"Dispatching node '{node_id}' with {len(states)} state(s).")

                if isinstance(node, AggregatorNode):
                    futures.append((node_id, self.executor.submit(self.execute_node_with_retry, node, states, self.retry_policy)))
                else:
                    state = states[0]
                    futures.append((node_id, self.executor.submit(self.execute_node_with_retry, node, state, self.retry_policy)))

            # Process results with timeout
            for node_id, future in futures:
                try:
                    result_state = future.result(timeout=superstep_timeout)
                    logging.info(f"Node '{node_id}' completed execution with result: {result_state}")
                    node = self.graph.nodes[node_id]
                    for edge in node.outgoing_edges:
                        if isinstance(edge, ConcreteEdge):
                            sink_id = edge.sink.node_id
                            next_active_states[sink_id].append(copy.deepcopy(result_state))
                            logging.info(f"State routed from '{node_id}' to '{sink_id}' via concrete edge.")
                        elif isinstance(edge, ConditionalEdge):
                            chosen_node_id = edge.routing_function(result_state)
                            if chosen_node_id not in [sink.node_id for sink in edge.sinks]:
                                raise GraphExecutionError(
                                    node.node_id,
                                    f"Routing function returned unknown sink '{chosen_node_id}' not in declared sinks {[sink.node_id for sink in edge.sinks]}"
                                )
                            next_active_states[chosen_node_id].append(copy.deepcopy(result_state))
                            logging.info(f"State routed from '{node_id}' to '{chosen_node_id}' via conditional edge.")

                    if node_id == self.graph.end_node.node_id:
                        final_state = result_state

                except concurrent.futures.TimeoutError:
                    logging.error(f"Execution of node '{node_id}' timed out after {superstep_timeout} seconds.")
                    raise GraphExecutionError(node_id, f"Node execution timed out after {superstep_timeout} seconds.")

                except Exception as e:
                    logging.error(f"Exception during execution of node '{node_id}': {e}")
                    raise GraphExecutionError(node_id, str(e))

            self.active_states = next_active_states
            superstep += 1

        if superstep >= max_supersteps:
            logging.error("Graph execution terminated: maximum supersteps reached without termination.")
            raise GraphExecutionError("N/A", "Maximum supersteps reached without termination.")

        logging.info("Graph execution completed successfully.")
        return final_state

# ----------------------------------------------------------------------
# Representational Graph Classes for Visualization
# ----------------------------------------------------------------------
class RepresentationalEdgeType(Enum):
    ConcreteEdgeRepresentation = 1
    ConditionalEdgeRepresentation = 2  # Note: using the provided spelling; adjust to "ConditionalEdgeRepresentation" if desired.

class RepresentationalNode:
    """
    A representation of an actual node in the graph.
    Each node has an id, a node type (e.g., 'processing' or 'aggregator'),
    and maintains lists of incoming and outgoing representational edges.
    """
    def __init__(self, node_id: str, node_type: str):
        self.node_id = node_id
        self.node_type = node_type
        self.incoming_edges: list[RepresentationalEdge] = []
        self.outgoing_edges: list[RepresentationalEdge] = []

    def __repr__(self) -> str:
        return f"RepresentationalNode(id={self.node_id}, type={self.node_type})"

class RepresentationalEdge:
    """
    A representation of an edge between two nodes in the graph.
    Contains source and sink RepresentationalNode objects and an edge type.
    """
    def __init__(self, source: RepresentationalNode, sink: RepresentationalNode, edge_type: RepresentationalEdgeType):
        self.source = source
        self.sink = sink
        self.edge_type = edge_type

    def __repr__(self) -> str:
        return f"RepresentationalEdge(source={self.source.node_id}, sink={self.sink.node_id}, type={self.edge_type.name})"

class RepresentationalGraph:
    """
    A collection of representational nodes and edges.
    Includes a helper method to convert an existing Graph (from GraphExecutorStatic)
    into a representational graph.
    """
    def __init__(self):
        # Use a dict for quick lookup by node id.
        self.nodes: dict[str, RepresentationalNode] = {}
        self.edges: list[RepresentationalEdge] = []

    @staticmethod
    def from_graph(graph: Graph) -> "RepresentationalGraph":
        rep_graph = RepresentationalGraph()
        # Create representational nodes.
        for node_id, node in graph.nodes.items():
            if hasattr(node, "func"):  # simple way to check for ProcessingNode
                node_type = "processing"
            elif node.__class__.__name__ == "AggregatorNode":
                node_type = "aggregator"
            else:
                node_type = "node"
            rep_node = RepresentationalNode(node_id, node_type)
            rep_graph.nodes[node_id] = rep_node

        # Create edges for concrete edges.
        for edge in graph.concrete_edges:
            src = rep_graph.nodes[edge.source.node_id]
            sink = rep_graph.nodes[edge.sink.node_id]
            rep_edge = RepresentationalEdge(src, sink, RepresentationalEdgeType.ConcreteEdgeRepresentation)
            rep_graph.edges.append(rep_edge)
            src.outgoing_edges.append(rep_edge)
            sink.incoming_edges.append(rep_edge)
            
        # Create edges for conditional edges (one for each branch).
        for cond_edge in graph.conditional_edges:
            src = rep_graph.nodes[cond_edge.source.node_id]
            for sink_node in cond_edge.sinks:
                sink = rep_graph.nodes[sink_node.node_id]
                rep_edge = RepresentationalEdge(src, sink, RepresentationalEdgeType.ConditionalEdgeRepresentation)
                rep_graph.edges.append(rep_edge)
                src.outgoing_edges.append(rep_edge)
                sink.incoming_edges.append(rep_edge)
                
        return rep_graph

class GraphVisualizer:
    """
    Visualizes the representational graph using a level-order layout starting from the 'start' node.
    - Nodes are arranged from top (start) to bottom.
    - Each node displays its id; aggregator nodes are given a distinct color.
    - Concrete edges are drawn as straight arrows while conditional edges are drawn as curved arrows.
    """
    def __init__(self, rep_graph):
        self.rep_graph = rep_graph

    def _compute_levels(self) -> dict[str, int]:
        """
        Computes level order (BFS) levels starting from the 'start' node.
        Returns a mapping from node_id to its level.
        """
        levels = {}
        start_id = "start"
        if start_id not in self.rep_graph.nodes:
            raise ValueError("No 'start' node found in the representational graph.")
        
        queue = deque([(start_id, 0)])
        visited = set()
        
        while queue:
            node_id, level = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            levels[node_id] = level
            node = self.rep_graph.nodes[node_id]
            for edge in node.outgoing_edges:
                queue.append((edge.sink.node_id, level + 1))
        
        return levels

    def visualize(self) -> None:
        levels = self._compute_levels()
        
        # Group nodes by level.
        level_nodes = defaultdict(list)
        for node_id, level in levels.items():
            level_nodes[level].append(node_id)

        # Assign positions for each node: x-coordinate spread within the level; y-coordinate based on level.
        pos = {}
        for level, nodes in level_nodes.items():
            count = len(nodes)
            for i, node_id in enumerate(sorted(nodes)):
                x = i - (count - 1) / 2.0  # center nodes horizontally at each level
                y = -level  # level 0 at the top
                pos[node_id] = (x, y)

        fig, ax = plt.subplots(figsize=(8, 6))

        # Draw nodes as circles.
        for node_id, (x, y) in pos.items():
            node = self.rep_graph.nodes[node_id]
            # Use a different color for aggregator nodes.
            if node.node_type == "aggregator":
                color = "lightcoral"
            else:
                color = "lightblue"
            
            circle = Circle(
                (x, y), 
                radius=0.3, 
                color=color, 
                ec="black", 
                zorder=2
            )
            ax.add_patch(circle)
            ax.text(x, y, node_id, ha="center", va="center", zorder=3)

        # Draw edges with arrows.
        for edge in self.rep_graph.edges:
            src_id = edge.source.node_id
            sink_id = edge.sink.node_id
            start_pos = pos[src_id]
            end_pos = pos[sink_id]

            # Decide arrow style based on edge type.
            if edge.edge_type.name == "ConcreteEdgeRepresentation":
                # Straight arrow, e.g., color='gray'
                color = "gray"
                connection_style = "arc3,rad=0.0"  # no curvature
                line_style = "solid"
            else:
                # Conditional edge: curved arrow, e.g., color='orange'
                color = "orange"
                connection_style = "arc3,rad=0.2"  # curved
                line_style = "dashed"

            arrow = FancyArrowPatch(
                start_pos, 
                end_pos,
                arrowstyle='-|>',         # a triangular arrowhead
                mutation_scale=15,        # size of arrowhead
                color=color,
                linewidth=2,
                linestyle=line_style,
                connectionstyle=connection_style,
                shrinkA=15,               # space between arrow start and node center
                shrinkB=15,               # space between arrow end and node center
                zorder=1
            )
            ax.add_patch(arrow)

        ax.autoscale()
        ax.axis('off')
        plt.tight_layout()
        plt.show()

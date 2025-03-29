import logging
import copy
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

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
    """Base exception for graph orchestration errors."""
    pass

class DuplicateNodeError(GraphOrchestratorException):
    def __init__(self, node_id: str) -> None:
        super().__init__(f"Node with id '{node_id}' already exists in the graph.")

class EdgeExistsError(GraphOrchestratorException):
    def __init__(self, source_id: str, sink_id: str) -> None:
        super().__init__(f"An edge from '{source_id}' to '{sink_id}' already exists.")

class NodeNotFoundError(GraphOrchestratorException):
    def __init__(self, node_id: str) -> None:
        super().__init__(f"Node with id '{node_id}' was not found in the graph.")

class GraphConfigurationError(GraphOrchestratorException):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class GraphExecutionError(Exception):
    def __init__(self, node_id: str, message: str) -> None:
        super().__init__(f"Error executing node '{node_id}': {message}")

# ----------------------------------------------------------------------
# State Class
# ----------------------------------------------------------------------
@dataclass
class State:
    data: Dict[str, Any] = field(default_factory=dict)
    def __repr__(self) -> str:
        return f"State({self.data})"

# ----------------------------------------------------------------------
# Routing Function Validator Decorator
# ----------------------------------------------------------------------
def routing_function(func: Callable[[State], str]) -> Callable[[State], str]:
    """
    Decorator to ensure a routing function returns a single string.
    """
    def wrapper(state: State) -> str:
        logging.info(f"Routing function '{func.__name__}' invoked with state: {state}")
        result = func(state)
        if not isinstance(result, str):
            logging.error(f"Routing function '{func.__name__}' returned a non-string value: {result}")
            raise ValueError("Routing function must return a single string representing the node id.")
        logging.info(f"Routing function '{func.__name__}' returned '{result}' for state: {state}")
        return result
    return wrapper

# ----------------------------------------------------------------------
# Abstract Node Base Class
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

# ----------------------------------------------------------------------
# Processing Node
# ----------------------------------------------------------------------
class ProcessingNode(Node):
    def __init__(self, node_id: str, func: Callable[[State], State]) -> None:
        super().__init__(node_id)
        self.func: Callable[[State], State] = func
        logging.info(f"ProcessingNode '{self.node_id}' created with processing function '{func.__name__}'.")

    def execute(self, state: State) -> State:
        logging.info(f"ProcessingNode '{self.node_id}' starting execution with input: {state}")
        result = self.func(state)
        logging.info(f"ProcessingNode '{self.node_id}' finished execution with output: {result}")
        return result

# ----------------------------------------------------------------------
# Aggregator Node
# ----------------------------------------------------------------------
class AggregatorNode(Node):
    def __init__(self, node_id: str) -> None:
        super().__init__(node_id)
        logging.info(f"AggregatorNode '{self.node_id}' created.")

    def execute(self, states: List[State]) -> State:
        logging.info(f"AggregatorNode '{self.node_id}' starting aggregation of {len(states)} states.")
        result = self.llm_merge(states)
        logging.info(f"AggregatorNode '{self.node_id}' completed aggregation with result: {result}")
        return result

    def llm_merge(self, states: List[State]) -> State:
        # Placeholder for LLM merging: simply combines all state dictionaries.
        merged_data: Dict[str, Any] = {}
        for state in states:
            merged_data.update(state.data)
        return State(data=merged_data)

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
        self.routing_function: Callable[[State], str] = routing_function(router)
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
        start_node = ProcessingNode("start", lambda state: state)
        end_node = ProcessingNode("end", lambda state: state)
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
        if sink_id not in self.graph.nodes:
            logging.error(f"Sink node '{sink_id}' not found.")
            raise NodeNotFoundError(sink_id)
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
        source = self.graph.nodes[source_id]
        sinks: List[Node] = []
        for sink_id in sink_ids:
            if sink_id not in self.graph.nodes:
                logging.error(f"Sink node '{sink_id}' not found for conditional edge.")
                raise NodeNotFoundError(sink_id)
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
    def __init__(self, graph: Graph, initial_state: State, max_workers: int = 4) -> None:
        logging.info("Initializing GraphExecutor...")
        self.graph: Graph = graph
        self.initial_state: State = initial_state
        self.max_workers: int = max_workers
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)
        # Map node_id to list of states pending execution.
        self.active_states: Dict[str, List[State]] = defaultdict(list)
        self.active_states[graph.start_node.node_id].append(initial_state)
        logging.info(f"GraphExecutor initialized. Starting at node '{graph.start_node.node_id}' with initial state: {initial_state}")

    def execute(self, max_supersteps: int = 100) -> Optional[State]:
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
                    futures.append((node_id, self.executor.submit(node.execute, states)))
                else:
                    if len(states) != 1:
                        logging.warning(f"ProcessingNode '{node_id}' received multiple states; using the first state.")
                    state = states[0]
                    futures.append((node_id, self.executor.submit(node.execute, state)))

            # Process results and route output state along outgoing edges.
            for node_id, future in futures:
                try:
                    result_state = future.result()
                    logging.info(f"Node '{node_id}' completed execution with result: {result_state}")
                    node = self.graph.nodes[node_id]
                    for edge in node.outgoing_edges:
                        if isinstance(edge, ConcreteEdge):
                            sink_id = edge.sink.node_id
                            next_active_states[sink_id].append(copy.deepcopy(result_state))
                            logging.info(f"State routed from '{node_id}' to '{sink_id}' via concrete edge.")
                        elif isinstance(edge, ConditionalEdge):
                            chosen_node_id = edge.routing_function(result_state)
                            next_active_states[chosen_node_id].append(copy.deepcopy(result_state))
                            logging.info(f"State routed from '{node_id}' to '{chosen_node_id}' via conditional edge.")
                    if node_id == self.graph.end_node.node_id:
                        final_state = result_state
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
# Sample Usage
# ----------------------------------------------------------------------
# Sample functions for processing nodes
def node1_func(state: State) -> State:
    logging.info("node1_func: Processing state...")
    state.data["node1"] = "processed"
    logging.info("node1_func: State processed.")
    return state

def node2_func(state: State) -> State:
    logging.info("node2_func: Processing state...")
    state.data["node2"] = "processed"
    logging.info("node2_func: State processed.")
    return state

def node3_func(state: State) -> State:
    logging.info("node3_func: Processing state...")
    state.data["node3"] = "processed"
    logging.info("node3_func: State processed.")
    return state

def node4_func(state: State) -> State:
    logging.info("node4_func: Processing state...")
    state.data["node4"] = "processed"
    # Decide next route based on state. Default to "end" if not specified.
    next_route = state.data.get("route", "end")
    state.data["next"] = next_route
    logging.info(f"node4_func: State processed. Next route set to '{next_route}'.")
    return state

# Routing function: returns the node id as a string.
@routing_function
def route1(state: State) -> str:
    return state.data.get("next", "end")

def main() -> None:
    logging.info("Starting main function to build and execute graph...")
    builder = GraphBuilder()

    # Create aggregator nodes.
    aggregator1 = AggregatorNode("aggregator1")
    aggregator2 = AggregatorNode("aggregator2")
    builder.add_aggregator(aggregator1)
    builder.add_aggregator(aggregator2)

    # Create additional processing nodes.
    node1 = ProcessingNode("node1", node1_func)
    node2 = ProcessingNode("node2", node2_func)
    node3 = ProcessingNode("node3", node3_func)
    node4 = ProcessingNode("node4", node4_func)

    # Add processing nodes.
    builder.add_node(node1)
    builder.add_node(node2)
    builder.add_node(node3)
    builder.add_node(node4)

    # Construct graph edges:
    # start -> aggregator1
    builder.add_concrete_edge("start", "aggregator1")
    # aggregator1 -> node1
    builder.add_concrete_edge("aggregator1", "node1")
    # node1 -> node2 and node1 -> node3
    builder.add_concrete_edge("node1", "node2")
    builder.add_concrete_edge("node1", "node3")
    # node2 -> aggregator2 and node3 -> aggregator2
    builder.add_concrete_edge("node2", "aggregator2")
    builder.add_concrete_edge("node3", "aggregator2")
    # aggregator2 -> node4
    builder.add_concrete_edge("aggregator2", "node4")
    # node4 -> {aggregator1, end} via a conditional edge.
    builder.add_conditional_edge("node4", ["aggregator1", "end"], route1)

    # Validate and build the graph.
    graph = builder.build_graph()

    # Define an initial state.
    initial_state = State(data={"route": "aggregator1"})  # Change "route" to "aggregator1" to loop back.

    # Create and run the GraphExecutor.
    executor = GraphExecutor(graph, initial_state, max_workers=4)
    try:
        final_state = executor.execute()
        logging.info(f"Final state after graph execution: {final_state}")
    except GraphExecutionError as e:
        logging.error(f"Graph execution failed: {e}")

if __name__ == "__main__":
    main()

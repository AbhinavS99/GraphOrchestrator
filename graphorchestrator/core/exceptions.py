class GraphOrchestratorException(Exception):
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
    def __init__(self, returned_value):
        super().__init__(f"Routing function must return a string, but got {type(returned_value).__name__}: {returned_value}")

class InvalidNodeActionOutput(GraphOrchestratorException):
    def __init__(self, returned_value):
        super().__init__(f"Node action must return a state, but got {type(returned_value).__name__}: {returned_value}")

class InvalidToolMethodOutput(GraphOrchestratorException):
    def __init__(self, returned_value):
        super().__init__(f"Tool method must return a state, but got {type(returned_value).__name__}: {returned_value}")

class NodeActionNotDecoratedError(GraphOrchestratorException):
    def __init__(self, func):
        name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{name}' passed to ProcessingNode must be decorated with @node_action.")

class RoutingFunctionNotDecoratedError(GraphOrchestratorException):
    def __init__(self, func):
        name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{name}' passed to ConditionalEdge must be decorated with @routing_function.")

class InvalidAggregatorActionError(GraphOrchestratorException):
    def __init__(self, returned_value):
        super().__init__(f"Aggregator action must return a state, but got {type(returned_value).__name__}")

class AggregatorActionNotDecorated(GraphOrchestratorException):
    def __init__(self, func):
        name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{name}' passed to Aggregator must be decorated with @aggregator_action")

class EmptyToolNodeDescriptionError(GraphOrchestratorException):
    def __init__(self, func):
        name = getattr(func, '__name__', repr(func))
        super().__init__(f"The tool function '{name}' has no description or docstring provided")

class ToolMethodNotDecorated(GraphOrchestratorException):
    def __init__(self, func):
        name = getattr(func, '__name__', repr(func))
        super().__init__(f"The function '{name}' passed to ToolNode has to be decorated with @tool_method")

class InvalidAIActionOutput(GraphOrchestratorException):
    def __init__(self, returned_value):
        super().__init__(f"AI action must return a state, but got {type(returned_value).__name__}")

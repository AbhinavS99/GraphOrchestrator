class GraphOrchestratorException(Exception):
    """
    Base exception for all exceptions raised by the graph orchestrator.
    """

    pass


class DuplicateNodeError(GraphOrchestratorException):
    """
    Exception raised when attempting to add a node with an ID that already exists.

    Attributes:
        node_id (str): The ID of the node that caused the error.
    """

    def __init__(self, node_id: str):
        """
        Initializes the DuplicateNodeError with the ID of the duplicate node.

        Args:
            node_id (str): The ID of the duplicate node.
        """
        super().__init__(f"Node with id '{node_id}' already exists.")
        self.node_id = node_id


class EdgeExistsError(GraphOrchestratorException):
    """
    Exception raised when attempting to add an edge that already exists.

    Attributes:
        source_id (str): The ID of the source node of the duplicate edge.
        sink_id (str): The ID of the sink node of the duplicate edge.
    """

    def __init__(self, source_id: str, sink_id: str):
        """
        Initializes the EdgeExistsError with the IDs of the source and sink nodes of the duplicate edge.

        Args:
            source_id (str): The ID of the source node of the duplicate edge.
            sink_id (str): The ID of the sink node of the duplicate edge.
        """
        super().__init__(f"Edge from '{source_id}' to '{sink_id}' already exists.")
        self.source_id = source_id
        self.sink_id = sink_id


class NodeNotFoundError(GraphOrchestratorException):
    """
    Exception raised when a requested node is not found in the graph.

    Attributes:
        node_id (str): The ID of the node that was not found.
    """

    def __init__(self, node_id: str):
        """
        Initializes the NodeNotFoundError with the ID of the node that was not found.

        Args:
            node_id (str): The ID of the node that was not found.
        """
        super().__init__(f"Node '{node_id}' not found in the graph.")
        self.node_id = node_id


class GraphConfigurationError(GraphOrchestratorException):
    """Exception raised when there is an error in the graph's configuration."""

    def __init__(self, message: str):
        """
        Initializes the GraphConfigurationError with a custom message.

        Args:
            message (str): The error message describing the configuration issue.
        """
        super().__init__(f"Graph configuration error: {message}")


class GraphExecutionError(GraphOrchestratorException):
    """
    Exception raised when an error occurs during the execution of the graph.

    Attributes:
        node_id (str): The ID of the node where the error occurred.
        message (str): The error message describing the execution issue.
    """

    def __init__(self, node_id: str, message: str):
        """
        Initializes the GraphExecutionError with the ID of the node where the error occurred and a custom message.

        Args:
            node_id (str): The ID of the node where the error occurred.
            message (str): The error message describing the execution issue.
        """
        super().__init__(f"Execution failed at node '{node_id}': {message}")
        self.node_id = node_id
        self.message = message


class InvalidRoutingFunctionOutput(GraphOrchestratorException):
    """Exception raised when a routing function does not return a string."""

    def __init__(self, returned_value):
        super().__init__(
            f"Routing function must return a string, but got {type(returned_value).__name__}: {returned_value}"
        )


class InvalidNodeActionOutput(GraphOrchestratorException):
    """Exception raised when a node action does not return a state."""

    def __init__(self, returned_value):
        super().__init__(
            f"Node action must return a state, but got {type(returned_value).__name__}: {returned_value}"
        )


class InvalidToolMethodOutput(GraphOrchestratorException):
    """Exception raised when a tool method does not return a state."""

    def __init__(self, returned_value):
        super().__init__(
            f"Tool method must return a state, but got {type(returned_value).__name__}: {returned_value}"
        )


class NodeActionNotDecoratedError(GraphOrchestratorException):
    def __init__(self, func):
        name = getattr(func, "__name__", repr(func))
        super().__init__(
            f"The function '{name}' passed to ProcessingNode must be decorated with @node_action."
        )


class RoutingFunctionNotDecoratedError(GraphOrchestratorException):
    def __init__(self, func):
        name = getattr(func, "__name__", repr(func))
        super().__init__(
            f"The function '{name}' passed to ConditionalEdge must be decorated with @routing_function."
        )


class InvalidAggregatorActionError(GraphOrchestratorException):
    """
    Exception raised when an aggregator action does not return a state.
    """

    def __init__(self, returned_value):
        super().__init__(
            f"Aggregator action must return a state, but got {type(returned_value).__name__}"
        )


class AggregatorActionNotDecorated(GraphOrchestratorException):
    """
    Exception raised when an aggregator function is not decorated with @aggregator_action.

    Attributes:
        func: The undecorated function.
    """

    def __init__(self, func):
        """
        Initializes the AggregatorActionNotDecorated with the undecorated function.

        Args:
            func: The undecorated function.
        """
        name = getattr(func, "__name__", repr(func))
        super().__init__(
            f"The function '{name}' passed to Aggregator must be decorated with @aggregator_action"
        )


class EmptyToolNodeDescriptionError(GraphOrchestratorException):
    """
    Exception raised when a tool function has no description or docstring.

    Attributes:
        func: The tool function with no description.
    """

    def __init__(self, func):
        """
        Initializes the EmptyToolNodeDescriptionError with the tool function missing a description.

        Args:
            func: The tool function missing a description.
        """
        name = getattr(func, "__name__", repr(func))
        super().__init__(
            f"The tool function '{name}' has no description or docstring provided"
        )


class ToolMethodNotDecorated(GraphOrchestratorException):
    """
    Exception raised when a tool method is not decorated with @tool_method.

    Attributes:
        func: The undecorated tool method.
    """

    def __init__(self, func):
        """
        Initializes the ToolMethodNotDecorated with the undecorated tool method.

        Args:
            func: The undecorated tool method.
        """
        name = getattr(func, "__name__", repr(func))
        super().__init__(
            f"The function '{name}' passed to ToolNode has to be decorated with @tool_method"
        )


class InvalidAIActionOutput(GraphOrchestratorException):
    """Exception raised when an AI action does not return a state."""

    def __init__(self, returned_value):
        super().__init__(
            f"AI action must return a state, but got {type(returned_value).__name__}"
        )

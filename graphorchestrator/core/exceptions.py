# Import necessary modules for logging and constants.
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class GraphOrchestratorException(Exception):
    """
    Base exception class for all exceptions raised by the graph orchestrator.
    It serves as the root of the custom exception hierarchy for this project.
    """

    pass


class DuplicateNodeError(GraphOrchestratorException):
    """
    Exception raised when a node with a duplicate ID is added to the graph.
    It logs an error message with relevant details.
    """

    def __init__(self, node_id: str):
        msg = f"Node with id '{node_id}' already exists."
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "duplicate_node",
                    LC.NODE_ID: node_id,
                },
            ),
        )
        super().__init__(msg)
        self.node_id = node_id


class EdgeExistsError(GraphOrchestratorException):
    """
    Exception raised when an attempt is made to create a duplicate edge in the graph.
    It logs an error message with information about the source and sink nodes.
    """

    def __init__(self, source_id: str, sink_id: str):
        msg = f"Edge from '{source_id}' to '{sink_id}' already exists."
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "duplicate_edge",
                    LC.SOURCE_NODE: source_id,
                    LC.SINK_NODE: sink_id,
                },
            ),
        )
        super().__init__(msg)
        self.source_id = source_id
        self.sink_id = sink_id


class NodeNotFoundError(GraphOrchestratorException):
    """
    Exception raised when a node is not found in the graph.
    It logs an error message with the ID of the missing node.
    """

    def __init__(self, node_id: str):
        msg = f"Node '{node_id}' not found in the graph."
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "node_not_found",
                    LC.NODE_ID: node_id,
                },
            ),
        )
        super().__init__(msg)
        self.node_id = node_id


class GraphConfigurationError(GraphOrchestratorException):
    """
    Exception raised when there's an error in the graph's configuration.
    It logs an error message with the details of the configuration issue.
    """

    def __init__(self, message: str):
        msg = f"Graph configuration error: {message}"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "graph",
                    LC.ACTION: "graph_config_error",
                    LC.CUSTOM: {"error": message},
                },
            ),
        )
        super().__init__(msg)


class GraphExecutionError(GraphOrchestratorException):
    """
    Exception raised when an error occurs during the graph's execution.
    It logs an error message with details about the failed node and the reason.
    """

    def __init__(self, node_id: str, message: str):
        msg = f"Execution failed at node '{node_id}': {message}"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "execution_failed",
                    LC.NODE_ID: node_id,
                    LC.CUSTOM: {"reason": message},
                },
            ),
        )
        super().__init__(msg)
        self.node_id = node_id
        self.message = message


class InvalidRoutingFunctionOutput(GraphOrchestratorException):
    """
    Exception raised when a routing function returns an invalid type.
    It logs an error message with information about the invalid return type.
    """

    def __init__(self, returned_value):
        msg = f"Routing function must return a string, but got {type(returned_value).__name__}: {returned_value}"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "invalid_routing_output",
                    LC.CUSTOM: {
                        "returned_type": str(type(returned_value)),
                        "value": str(returned_value)[:100],
                    },
                },
            ),
        )
        super().__init__(msg)


class InvalidNodeActionOutput(GraphOrchestratorException):
    """
    Exception raised when a node's action returns an invalid type.
    It logs an error message with information about the invalid return type.
    """

    def __init__(self, returned_value):
        msg = f"Node action must return a state, but got {type(returned_value).__name__}: {returned_value}"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "invalid_node_output",
                    LC.CUSTOM: {
                        "returned_type": str(type(returned_value)),
                        "value": str(returned_value)[:100],
                    },
                },
            ),
        )
        super().__init__(msg)


class InvalidToolMethodOutput(GraphOrchestratorException):
    """
    Exception raised when a tool method returns an invalid type.
    It logs an error message with information about the invalid return type.
    """

    def __init__(self, returned_value):
        msg = f"Tool method must return a state, but got {type(returned_value).__name__}: {returned_value}"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.ACTION: "invalid_tool_output",
                    LC.CUSTOM: {
                        "returned_type": str(type(returned_value)),
                        "value": str(returned_value)[:100],
                    },
                },
            ),
        )
        super().__init__(msg)


class NodeActionNotDecoratedError(GraphOrchestratorException):
    """
    Exception raised when a node's action function is not decorated with @node_action.
    It logs an error message with the name of the undecorated function.
    """

    def __init__(self, func):
        name = getattr(func, "__name__", repr(func))
        msg = f"The function '{name}' passed to ProcessingNode must be decorated with @node_action."
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "missing_node_action_decorator",
                    LC.CUSTOM: {"function": name},
                },
            ),
        )
        super().__init__(msg)


class RoutingFunctionNotDecoratedError(GraphOrchestratorException):
    """
    Exception raised when a routing function is not decorated with @routing_function.
    It logs an error message with the name of the undecorated function.
    """

    def __init__(self, func):
        name = getattr(func, "__name__", repr(func))
        msg = f"The function '{name}' passed to ConditionalEdge must be decorated with @routing_function."
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "missing_routing_function_decorator",
                    LC.CUSTOM: {"function": name},
                },
            ),
        )
        super().__init__(msg)


class InvalidAggregatorActionError(GraphOrchestratorException):
    """
    Exception raised when an aggregator action returns an invalid type.
    It logs an error message with the invalid return type.
    """

    def __init__(self, returned_value):
        msg = f"Aggregator action must return a state, but got {type(returned_value).__name__}"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "invalid_aggregator_output",
                    LC.CUSTOM: {"returned_type": str(type(returned_value))},
                },
            ),
        )
        super().__init__(msg)


class AggregatorActionNotDecorated(GraphOrchestratorException):
    """
    Exception raised when an aggregator action function is not decorated with @aggregator_action.
    It logs an error message with the name of the undecorated function.
    """

    def __init__(self, func):
        name = getattr(func, "__name__", repr(func))
        msg = f"The function '{name}' passed to Aggregator must be decorated with @aggregator_action"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "missing_aggregator_decorator",
                    LC.CUSTOM: {"function": name},
                },
            ),
        )
        super().__init__(msg)


class EmptyToolNodeDescriptionError(GraphOrchestratorException):
    """
    Exception raised when a tool function lacks a description or docstring.
    It logs an error message indicating the missing description.
    """

    def __init__(self, func):
        name = getattr(func, "__name__", repr(func))
        msg = f"The tool function '{name}' has no description or docstring provided"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.ACTION: "missing_description",
                    LC.CUSTOM: {"function": name},
                },
            ),
        )
        super().__init__(msg)


class ToolMethodNotDecorated(GraphOrchestratorException):
    """
    Exception raised when a tool method is not decorated with @tool_method.
    It logs an error message with the name of the undecorated method.
    """

    def __init__(self, func):
        name = getattr(func, "__name__", repr(func))
        msg = f"The function '{name}' passed to ToolNode has to be decorated with @tool_method"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.ACTION: "missing_tool_method_decorator",
                    LC.CUSTOM: {"function": name},
                },
            ),
        )
        super().__init__(msg)


class InvalidAIActionOutput(GraphOrchestratorException):
    """
    Exception raised when an AI action returns an invalid type.
    It logs an error message with information about the invalid return type.
    """

    def __init__(self, returned_value):
        msg = f"AI action must return a state, but got {type(returned_value).__name__}"
        GraphLogger.get().error(
            msg,
            **wrap_constants(
                message=msg,
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "invalid_ai_output",
                    LC.CUSTOM: {"returned_type": str(type(returned_value))},
                },
            ),
        )
        super().__init__(msg)

from enum import Enum


class LogConstants(str, Enum):
    # ──────────────── Meta Info ────────────────
    TIMESTAMP = "timestamp"  # ISO 8601 UTC timestamp
    LEVEL = "level"  # INFO / DEBUG / ERROR
    MESSAGE = "message"  # Human-readable description
    THREAD = "thread"  # Thread name (e.g., MainThread, Worker-1)

    # ──────────────── Execution Context ────────────────
    RUN_ID = "run_id"  # UUID per graph execution
    GRAPH_NAME = "graph_name"  # Optional: user-defined name
    SUPERSTEP = "superstep"  # Execution iteration number

    # ──────────────── Node Metadata ────────────────
    EVENT_TYPE = "event_type"  # e.g. node, edge, retry, fallback, tool_call, graph
    NODE_ID = "node_id"  # Node identifier
    NODE_TYPE = "node_type"  # ProcessingNode, AggregatorNode, ToolNode, etc.
    ACTION = "action"  # e.g., execute_start, execute_end, created, failed

    # ──────────────── Edge Metadata ────────────────
    SOURCE_NODE = "source_node"  # Source node of an edge
    SINK_NODE = "sink_node"  # Sink node of an edge
    EDGE_TYPE = "edge_type"  # "concrete" or "conditional"
    ROUTER_FUNC = "router_function"  # Name of routing function, if applicable
    ROUTED_TO = "routed_to"  # Output of routing function

    # ──────────────── Retry & Fallback ────────────────
    RETRY_COUNT = "retry_count"  # Current attempt
    MAX_RETRIES = "max_retries"  # Allowed attempts
    RETRY_DELAY = "retry_delay"  # Delay before next retry (s)
    BACKOFF = "retry_backoff"  # Backoff multiplier
    TIMEOUT = "timeout"  # Node-level or superstep-level timeout (s)
    FALLBACK_NODE = "fallback_node"  # Target fallback node, if used
    FALLBACK_SUCCESS = "fallback_success"  # True/False

    # ──────────────── I/O & Performance ────────────────
    INPUT_SIZE = "input_size"  # len(state.messages) before execution
    OUTPUT_SIZE = "output_size"  # len(state.messages) after execution
    DURATION_MS = "duration_ms"  # Execution time in milliseconds
    SUCCESS = "success"  # True/False for status

    # ──────────────── External Context (Optional) ────────────────
    USER_ID = "user_id"  # Optional: Who triggered it
    HOSTNAME = "hostname"  # For distributed runs
    REQUEST_ID = "request_id"  # Optional: external traceability

    # ──────────────── Catch-all (Custom/Debug) ────────────────
    CUSTOM = "custom"  # Arbitrary JSON blob (for extra debug info)

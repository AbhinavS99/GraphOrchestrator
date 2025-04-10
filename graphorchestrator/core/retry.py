from dataclasses import dataclass

@dataclass
class RetryPolicy:
    max_retries: int = 3       # Maximum number of retries
    delay: float = 1.0         # Initial delay in seconds
    backoff: float = 2.0       # Factor by which delay increases on each retry

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """
    Defines a retry policy with configurable parameters.

    Attributes:
        max_retries (int): The maximum number of times to retry an operation.
        delay (float): The initial delay in seconds before the first retry.
        backoff (float): The factor by which to increase the delay after each retry.

    Example:
        policy = RetryPolicy(max_retries=5, delay=0.5, backoff=1.5)
    """

    max_retries: int = 3
    delay: float = 1.0
    backoff: float = 2.0

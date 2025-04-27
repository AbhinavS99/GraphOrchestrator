from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """
    Defines a retry policy with configurable parameters.

    Attributes:
        max_retries (int): The maximum number of times to retry an operation.
        delay (float): The initial delay in seconds before the first retry.
        backoff (float): The factor by which to increase the delay after each retry.
    """

    max_retries: int = 3
    delay: float = 1.0
    backoff: float = 2.0

    def __str__(self) -> str:
        return f"RetryPolicy(max_retries={self.max_retries}, delay={self.delay:.2f}s, backoff={self.backoff:.2f}x)"

    def __repr__(self) -> str:
        return str(self)  # same as __str__, unless you want a different debug style

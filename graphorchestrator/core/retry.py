from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """
    Configuration for retrying failed operations during graph execution.

    A `RetryPolicy` defines how many times an operation should be retried upon failure,
    how long to wait between attempts, and how delay is scaled using exponential backoff.

    Attributes
    ----------
    `max_retries` : `int`
        The maximum number of retry attempts allowed for a single operation.

    `delay` : `float`
        The initial delay (in seconds) before the first retry attempt.

    `backoff` : `float`
        The multiplier applied to the delay after each failed attempt. A value of 2.0 doubles
        the wait time after every retry.

    Examples
    --------
    Create a default policy:

    ```python
    policy = RetryPolicy()
    print(policy)
    # Output: RetryPolicy(max_retries=3, delay=1.00s, backoff=2.00x)
    ```

    Customize retry behavior:

    ```python
    custom = RetryPolicy(max_retries=5, delay=0.5, backoff=1.5)
    print(custom)
    # Output: RetryPolicy(max_retries=5, delay=0.50s, backoff=1.50x)
    ```
    """

    max_retries: int = 3
    delay: float = 1.0
    backoff: float = 2.0

    def __str__(self) -> str:
        """
        Returns a readable string representation of the retry policy.

        Returns
        -------
        `str`
            Human-readable summary of the retry configuration.
        """
        return f"RetryPolicy(max_retries={self.max_retries}, delay={self.delay:.2f}s, backoff={self.backoff:.2f}x)"

    def __repr__(self) -> str:
        """
        Returns the same representation as `__str__` for debugging purposes.

        Returns
        -------
        `str`
            Debug-friendly string identical to `__str__`.
        """
        return str(self)

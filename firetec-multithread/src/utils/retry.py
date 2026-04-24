"""Utilitários de retry com backoff."""
import time
from typing import Callable, Tuple, Type


def with_retry(
    fn: Callable,
    retries: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 5.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    delay = initial_delay
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except exceptions as exc:  # noqa: PERF203
            last_error = exc
            if attempt == retries:
                break
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
    raise last_error

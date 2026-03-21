import time
from typing import Callable


def start_ms_timer() -> Callable[[], float]:
    """
    Initializes a timer and returns a function to get elapsed time.

    Returns:
        A function that calculates elapsed milliseconds when called.
    """
    start = time.time()

    def _get_elapsed() -> float:
        return (time.time() - start) * 1000

    return _get_elapsed

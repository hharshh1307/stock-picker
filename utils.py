import logging
import time
import random
import functools
from typing import Any, Callable, Optional

from config import LOG_FORMAT, LOG_DATE_FORMAT, LOG_DIR


def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    logger.addHandler(console)

    if log_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(LOG_DIR / log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(fh)

    return logger


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 5.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    logging.getLogger(func.__module__).warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator


class RateLimiter:
    def __init__(self, min_delay: float = 1.0, max_delay: Optional[float] = None):
        self.min_delay = min_delay
        self.max_delay = max_delay or min_delay
        self._last_call: float = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_call
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_call = time.monotonic()


def process_in_batches(
    items: list,
    batch_size: int,
    processor: Callable,
    delay_between_batches: float = 3.0,
) -> list[tuple[Any, bool, Optional[str]]]:
    results: list[tuple[Any, bool, Optional[str]]] = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        for item in batch:
            try:
                processor(item)
                results.append((item, True, None))
            except Exception as e:
                results.append((item, False, str(e)))
        if i + batch_size < len(items):
            time.sleep(delay_between_batches)
    return results

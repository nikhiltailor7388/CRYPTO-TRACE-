import logging
import time

logger = logging.getLogger("cryptotrace")


def call_with_retry(fn, *args, max_attempts=3, backoff_seconds=2, **kwargs):
    """Retry a network call on rate-limit errors while keeping the behaviour deterministic."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except RuntimeError as exc:
            if str(exc) == "RATE_LIMIT" and attempt < max_attempts:
                wait = backoff_seconds * attempt
                logger.warning("Rate limited on API call, retry %s in %ss", attempt, wait)
                time.sleep(wait)
                continue
            raise

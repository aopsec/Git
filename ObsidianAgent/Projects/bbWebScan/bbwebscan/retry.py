import time
from collections.abc import Callable

from bbwebscan.models import RetryPolicy


def with_retry[T](
    fn: Callable[[], T],
    *,
    policy: RetryPolicy,
    is_transient: Callable[[T], bool],
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[T, int]:
    """Run ``fn`` up to ``policy.max_attempts`` times.

    ``is_transient`` decides whether the result warrants a retry. Returns the
    final result and the number of attempts performed (1-based).
    """
    attempt = 1
    while True:
        result = fn()
        if attempt >= policy.max_attempts or not is_transient(result):
            return result, attempt
        sleep(policy.backoff_s * (2 ** (attempt - 1)))
        attempt += 1

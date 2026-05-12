from bbwebscan.models import RetryPolicy
from bbwebscan.retry import with_retry


def test_with_retry_succeeds_first_attempt() -> None:
    calls = {"n": 0}

    def fn() -> int:
        calls["n"] += 1
        return 0

    result, attempts = with_retry(
        fn, policy=RetryPolicy(max_attempts=3), is_transient=lambda r: r != 0,
        sleep=lambda _: None,
    )
    assert result == 0
    assert attempts == 1
    assert calls["n"] == 1


def test_with_retry_retries_until_success() -> None:
    sequence = iter([1, 1, 0])

    def fn() -> int:
        return next(sequence)

    result, attempts = with_retry(
        fn, policy=RetryPolicy(max_attempts=5), is_transient=lambda r: r != 0,
        sleep=lambda _: None,
    )
    assert result == 0
    assert attempts == 3


def test_with_retry_stops_at_max_attempts() -> None:
    def fn() -> int:
        return 1

    result, attempts = with_retry(
        fn, policy=RetryPolicy(max_attempts=2), is_transient=lambda r: True,
        sleep=lambda _: None,
    )
    assert result == 1
    assert attempts == 2


def test_with_retry_sleeps_with_exponential_backoff() -> None:
    sleeps: list[float] = []
    sequence = iter([1, 1, 0])

    with_retry(
        lambda: next(sequence),
        policy=RetryPolicy(max_attempts=4, backoff_s=1.0),
        is_transient=lambda r: r != 0,
        sleep=sleeps.append,
    )
    assert sleeps == [1.0, 2.0]

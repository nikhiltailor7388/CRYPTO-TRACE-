from backend.adapters.resilient import call_with_retry


def test_retry_on_rate_limit():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("RATE_LIMIT")
        return "ok"

    assert call_with_retry(flaky, max_attempts=3, backoff_seconds=0) == "ok"
    assert attempts["count"] == 3

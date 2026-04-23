import pytest
from services.training_worker.worker import sync_retry


def test_retry_success_after_fail():
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise Exception("fail")
        return "ok"

    result = sync_retry(flaky, retries=3)
    assert result == "ok"
    assert calls["count"] == 2


def test_retry_fail_all():
    def always_fail():
        raise Exception("fail")

    with pytest.raises(Exception):
        sync_retry(always_fail, retries=3)

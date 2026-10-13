import pytest

from src.limiter import RateLimiter


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


def test_a_burst_passes_then_the_next_request_waits_one_interval(clock):
    limiter = RateLimiter(3, 2.0, clock=clock)

    assert [limiter.hit(1).allowed for _ in range(3)] == [True, True, True]

    refused = limiter.hit(1)

    assert not refused.allowed
    assert refused.retry_after == pytest.approx(2.0)

    clock.now += 0.5

    assert limiter.hit(1).retry_after == pytest.approx(1.5)


def test_only_the_first_refusal_of_a_streak_warns(clock):
    limiter = RateLimiter(1, 10.0, clock=clock)
    limiter.hit(1)

    assert [limiter.hit(1).warn for _ in range(3)] == [True, False, False]

    clock.now += 10.0

    assert limiter.hit(1).allowed
    assert limiter.hit(1).warn  # a new streak


def test_requests_refused_while_flooding_do_not_delay_recovery(clock):
    limiter = RateLimiter(2, 1.0, clock=clock)
    limiter.hit(1)
    limiter.hit(1)

    for _ in range(50):
        clock.now += 0.01
        limiter.hit(1)

    clock.now = 1001.0

    assert limiter.hit(1).allowed


def test_one_request_comes_back_per_interval(clock):
    limiter = RateLimiter(5, 2.0, clock=clock)

    for _ in range(5):
        limiter.hit(1)

    clock.now += 4.0

    assert [limiter.hit(1).allowed for _ in range(3)] == [True, True, False]


def test_an_idle_key_gets_its_whole_burst_back(clock):
    limiter = RateLimiter(4, 1.0, clock=clock, sweep_interval=0.5)

    for _ in range(4):
        limiter.hit(1)

    clock.now += 60.0  # past a sweep, which forgets the key

    assert [limiter.hit(1).allowed for _ in range(5)] == [True] * 4 + [False]


def test_keys_have_budgets_of_their_own(clock):
    limiter = RateLimiter(1, 5.0, clock=clock)

    assert limiter.hit(1).allowed
    assert not limiter.hit(1).allowed
    assert limiter.hit(2).allowed

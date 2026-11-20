"""The statistics behind the linkage engine (also cross-checked against SciPy
during development; see docs/health-linkage-method.md)."""

import math

import pytest

from app.services.linkage_stats import _ranks, poisson_rate_test_greater, spearman


def exact_tail(x, n, p):
    return sum(math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(x, n + 1))


@pytest.mark.parametrize(
    "xf,tf,xb,tb", [(5, 7, 10, 28), (30, 28, 50, 56), (0, 7, 3, 7), (12, 31, 0, 62)]
)
def test_matches_the_binomial_formula(xf, tf, xb, tb):
    expected = exact_tail(xf, xf + xb, tf / (tf + tb))
    assert poisson_rate_test_greater(xf, tf, xb, tb) == pytest.approx(expected, rel=1e-9)


def test_equal_rates_are_not_significant_and_large_rises_are():
    assert poisson_rate_test_greater(72, 28, 144, 56) > 0.4
    assert poisson_rate_test_greater(160, 28, 144, 56) < 1e-6


def test_large_counts_do_not_overflow():
    p = poisson_rate_test_greater(5000, 28, 8000, 56)
    assert 0 <= p < 1e-10


def test_no_visits_gives_p_one():
    assert poisson_rate_test_greater(0, 28, 0, 56) == 1.0


def test_ranks_average_ties():
    assert _ranks([10, 20, 20, 5]) == [2, 3.5, 3.5, 1]


def test_spearman():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    assert spearman([1, 2, 3], [1, 2, 3]) is None  # too few points
    assert spearman([0, 0, 0, 0], [1, 2, 3, 4]) is None  # no variation

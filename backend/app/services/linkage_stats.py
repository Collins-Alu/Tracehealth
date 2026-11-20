"""
Statistics used by the health-linkage engine, written out in plain Python so
every step can be read and checked (see docs/health-linkage-method.md).
"""

import math


def poisson_rate_test_greater(
    followup_visits: int, followup_days: float, baseline_visits: int, baseline_days: float
) -> float:
    """
    One-sided exact test that the follow-up visit RATE is higher than the
    baseline rate (conditional binomial test for two Poisson counts).

    If both periods had the same daily rate, then given the total number of
    visits N = x_f + x_b, the follow-up count would follow a binomial
    distribution with p0 = t_f / (t_f + t_b), where t is the number of days
    observed. The p-value is P(X >= x_f) for X ~ Binomial(N, p0): the chance
    of seeing this many (or more) follow-up visits by luck alone.
    """
    n = followup_visits + baseline_visits
    if n == 0:
        return 1.0
    p0 = followup_days / (followup_days + baseline_days)
    if p0 <= 0:
        return 1.0 if followup_visits == 0 else 0.0
    if p0 >= 1:
        return 1.0
    log_p, log_q = math.log(p0), math.log1p(-p0)
    log_terms = [
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * log_p
        + (n - k) * log_q
        for k in range(followup_visits, n + 1)
    ]
    peak = max(log_terms)  # sum in log space to avoid underflow
    total = peak + math.log(sum(math.exp(t - peak) for t in log_terms))
    return min(1.0, math.exp(total))


def _ranks(values: list[float]) -> list[float]:
    """Ranks starting at 1, with tied values given the average of their ranks."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float], min_points: int = 4) -> float | None:
    """Spearman rank correlation (-1..1), or None when it can't be measured
    (too few points, or one series never changes)."""
    if len(x) != len(y) or len(x) < min_points:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return max(-1.0, min(1.0, cov / math.sqrt(vx * vy)))

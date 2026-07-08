"""Wilson score interval machinery.

All coverage/robustness statistics in the system are Wilson intervals over
*evidence cells* (never raw points).  The formulas here are the ones written
in the design:

    center     = (p_hat + z^2 / 2n) / (1 + z^2 / n)
    half-width = z / (1 + z^2/n) * sqrt(p_hat (1 - p_hat) / n + z^2 / (4 n^2))
"""

from __future__ import annotations

import math


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k successes out of n trials.

    Returns (lo, hi), clipped to [0, 1].  n == 0 returns the vacuous (0, 1).
    """
    if n <= 0:
        return (0.0, 1.0)
    p_hat = k / n
    z2n = z * z / n
    center = (p_hat + z2n / 2.0) / (1.0 + z2n)
    half = (z / (1.0 + z2n)) * math.sqrt(
        p_hat * (1.0 - p_hat) / n + z * z / (4.0 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def n_all_pass_clears(theta: float, z: float = 1.96) -> int:
    """Smallest n such that an all-pass sample's Wilson lower bound clears theta.

    With p_hat = 1 the Wilson lower bound reduces to n / (n + z^2), so the
    answer is the smallest integer n with n / (n + z^2) > theta.  This is the
    decide-in-one-round evidence-cell allocation for settlements >= P0
    (theta = 0.90, z = 1.96 gives 35) — computed, never hardcoded.
    """
    n = math.floor(theta * z * z / (1.0 - theta)) + 1
    # guard against floating-point edge cases
    while n / (n + z * z) <= theta:
        n += 1
    return n

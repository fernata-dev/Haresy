"""Statistics used by every report: Wilson interval and exact McNemar test."""
from __future__ import annotations

import math

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float | None, float | None]:
    """Wilson score interval for a binomial proportion k/n (no continuity correction)."""
    if n <= 0:
        return None, None
    if not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n")
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    lo = 0.0 if k == 0 else max(0.0, centre - half)
    hi = 1.0 if k == n else min(1.0, centre + half)
    return lo, hi


def cell(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {
        "k": k, "n": n,
        "rate": (k / n) if n else None,
        "ci_lo": lo, "ci_hi": hi,
    }


def mcnemar_exact(b: int, c: int) -> float | None:
    """Two-sided exact McNemar p-value from the discordant counts b and c.

    b = cases where A succeeded and B did not; c = the reverse.  Under H0 the
    discordant pairs are Binomial(b+c, 0.5).  Returns None when b+c == 0
    (no discordant pair: the test is undefined, not "p = 1").
    """
    n = b + c
    if n == 0:
        return None
    m = min(b, c)
    tail = sum(math.comb(n, i) for i in range(m + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def intervals_overlap(a: dict, b: dict) -> bool | None:
    """Do two Wilson intervals overlap?  None if either cell is empty."""
    if a.get("ci_lo") is None or b.get("ci_lo") is None:
        return None
    return not (a["ci_lo"] > b["ci_hi"] or b["ci_lo"] > a["ci_hi"])

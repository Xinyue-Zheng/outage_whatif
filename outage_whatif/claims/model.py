"""Claim model.

Every claim has: ID, type, subject, three-valued state, a written
adjudication procedure (the functions in adjudicate.py), and — while
undecided — a named remedy.  Supported capacity claims are always phrased
"no capacity obstacle found" (necessary conditions only).
"""

from __future__ import annotations

from dataclasses import dataclass, field

SUPPORTED = "supported"
REFUTED = "refuted"
UNDECIDED = "undecided"

COVERAGE = "coverage"
CAPACITY = "capacity"
ROBUSTNESS = "robustness"
INTEGRITY = "integrity"


@dataclass
class Claim:
    cid: str
    ctype: str
    subject: str                    # subregion sid | neighbor site/cell | sector
    state: str = UNDECIDED
    remedy: str = ""                # named remedy while undecided
    ticket: bool = False            # flip test says spending on it can matter
    detail: dict = field(default_factory=dict)
    alive: bool = True
    parent: str | None = None
    children: list = field(default_factory=list)
    born_round: int = 0
    rounds_undecided: int = 0
    densifications: int = 0         # coverage: densification rounds consumed
    drilled: bool = False           # capacity: drilled down to per-cell children

    def statement(self) -> str:
        if self.ctype == COVERAGE:
            return (f"the vast majority of footprint evidence cells in "
                    f"{self.subject} have a qualifying best alternative")
        if self.ctype == CAPACITY:
            return f"no capacity obstacle found at {self.subject}"
        if self.ctype == ROBUSTNESS:
            return (f"best alternatives in {self.subject} are not concentrated "
                    f"in one owner site")
        return (f"the ring outside boundary sector {self.subject} contains "
                f"essentially no footprint points")


class ClaimSet:
    """All claims of a run, alive and dead."""

    def __init__(self):
        self._c: dict[str, Claim] = {}

    def add(self, claim: Claim) -> Claim:
        if claim.cid in self._c:
            raise KeyError(f"duplicate claim id {claim.cid}")
        self._c[claim.cid] = claim
        return claim

    def get(self, cid: str) -> Claim:
        return self._c[cid]

    def __contains__(self, cid: str) -> bool:
        return cid in self._c

    def alive(self) -> list[Claim]:
        return [c for c in self._c.values() if c.alive]

    def open(self) -> list[Claim]:
        """Open = alive and undecided (the flip test's domain)."""
        return [c for c in self._c.values() if c.alive and c.state == UNDECIDED]

    def by_type(self, ctype: str, alive_only: bool = True) -> list[Claim]:
        return [c for c in self._c.values()
                if c.ctype == ctype and (c.alive or not alive_only)]

    def all(self) -> list[Claim]:
        return list(self._c.values())

    def states(self) -> dict:
        return {c.cid: c.state for c in self.alive()}

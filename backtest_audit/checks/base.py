"""Check protocol and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from backtest_audit.models import Backtest


class Severity(str, Enum):
    """How much a finding should change your belief in the result.

    BLOCKING means the headline number does not measure what it claims to;
    it is not a style opinion. WARNING means the number may be real but is
    not comparable or not yet significant. SKIPPED means the artifact did
    not carry enough information to judge — reported, never hidden, because
    a silent skip reads as a pass.
    """

    BLOCKING = "blocking"
    WARNING = "warning"
    PASS = "pass"
    SKIPPED = "skipped"


@dataclass
class Finding:
    check_id: str
    title: str
    severity: Severity
    summary: str
    detail: str = ""
    remedy: str = ""
    evidence: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.severity in (Severity.PASS, Severity.SKIPPED)


class Check(Protocol):
    id: str
    title: str

    def run(self, bt: Backtest) -> Finding: ...


def skipped(check_id: str, title: str, why: str) -> Finding:
    return Finding(
        check_id=check_id,
        title=title,
        severity=Severity.SKIPPED,
        summary=f"not enough information to judge — {why}",
        remedy="Export the missing field and re-run; an unjudged check is not a passed check.",
    )

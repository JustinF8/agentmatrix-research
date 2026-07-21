from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AttributionBucket:
    dimension: str
    name: str
    contribution: float
    contribution_pct: float
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AttributionSummary:
    total_return: float
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    fee_drag: float = 0.0
    slippage_drag: float = 0.0
    cash_drag: float = 0.0


@dataclass(slots=True)
class AttributionReport:
    summary: AttributionSummary
    buckets: list[AttributionBucket] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    methodology: str = "basic-v1"

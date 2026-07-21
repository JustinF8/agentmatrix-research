from __future__ import annotations

from contracts.attribution import AttributionBucket, AttributionReport, AttributionSummary


def build_basic_attribution(
    total_return: float,
    benchmark_return: float = 0.0,
    fee_drag: float = 0.0,
    slippage_drag: float = 0.0,
    cash_drag: float = 0.0,
    position_contributions: dict[str, float] | None = None,
    sector_contributions: dict[str, float] | None = None,
) -> AttributionReport:
    excess_return = total_return - benchmark_return
    summary = AttributionSummary(
        total_return=total_return,
        benchmark_return=benchmark_return,
        excess_return=excess_return,
        fee_drag=fee_drag,
        slippage_drag=slippage_drag,
        cash_drag=cash_drag,
    )
    buckets: list[AttributionBucket] = []
    total_base = abs(total_return) if abs(total_return) > 1e-12 else 1.0
    for name, value in (position_contributions or {}).items():
        buckets.append(AttributionBucket("position", name, value, value / total_base))
    for name, value in (sector_contributions or {}).items():
        buckets.append(AttributionBucket("sector", name, value, value / total_base))
    buckets.extend([
        AttributionBucket("cost", "fee_drag", fee_drag, fee_drag / total_base),
        AttributionBucket("cost", "slippage_drag", slippage_drag, slippage_drag / total_base),
        AttributionBucket("cash", "cash_drag", cash_drag, cash_drag / total_base),
    ])
    return AttributionReport(summary=summary, buckets=buckets, methodology="basic-v1")

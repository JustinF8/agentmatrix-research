from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StrategyMetadata:
    strategy_id: str
    name: str
    version: str = "v1"
    source: str = "internal"
    source_engine: str = "generic"
    execution_engine: str = "gm"
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StrategyContext:
    run_id: str
    as_of: str
    benchmark: str
    universe: list[str] = field(default_factory=list)
    dataset_id: str = ""
    execution_mode: str = "backtest"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TargetPosition:
    symbol: str
    target_weight: float
    side: str = "long"
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StrategyDecision:
    metadata: StrategyMetadata
    context: StrategyContext
    targets: list[TargetPosition]
    parameters: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    raw_signals: list[dict[str, Any]] = field(default_factory=list)


class StrategyKernel:
    def metadata(self) -> StrategyMetadata:
        raise NotImplementedError

    def generate_decision(self, context: StrategyContext, market_data: Any) -> StrategyDecision:
        raise NotImplementedError

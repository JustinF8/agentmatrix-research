from __future__ import annotations

from contracts.strategy import StrategyContext, StrategyKernel, StrategyMetadata


class BaseStrategyKernel(StrategyKernel):
    def __init__(self, metadata: StrategyMetadata):
        self._metadata = metadata

    def metadata(self) -> StrategyMetadata:
        return self._metadata

    def generate_decision(self, context: StrategyContext, market_data):
        raise NotImplementedError

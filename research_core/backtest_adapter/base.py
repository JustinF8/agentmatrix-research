from __future__ import annotations

from contracts.backtest import BacktestRequest, BacktestResult


class BacktestAdapter:
    engine_name = "generic"

    def validate(self, request: BacktestRequest) -> None:
        if not request.module_path:
            raise ValueError("module_path is required")
        if not request.start_time or not request.end_time:
            raise ValueError("start_time and end_time are required")

    def run(self, request: BacktestRequest) -> BacktestResult:
        raise NotImplementedError

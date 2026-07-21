from .base import BaseStrategyKernel
from .backtest_engine import (
    run_backtest, calculate_performance_metrics, calculate_transaction_cost,
    calculate_turnover, find_rebalance_dates, generate_nav_output,
    TradeCosts, BacktestResult
)
from .templates.phoenix_templates import (
    StrategyTemplate, PHOENIX_TEMPLATES, get_template, list_templates,
    apply_template, template_docstring
)

__all__ = [
    "BaseStrategyKernel",
    "run_backtest",
    "calculate_performance_metrics",
    "calculate_transaction_cost",
    "calculate_turnover",
    "find_rebalance_dates",
    "generate_nav_output",
    "TradeCosts",
    "BacktestResult",
    "StrategyTemplate",
    "PHOENIX_TEMPLATES",
    "get_template",
    "list_templates",
    "apply_template",
    "template_docstring",
]

"""
Phoenix Strategy Templates — 从 v2 到 v20 的策略演进总结

策略演进路径:
v2-v8: 基础因子轮动 → 单因子→多因子过渡
v9-v11: 真实化 → 引入成本/滑点/容量约束
v12: 因子分解 → 收益拆解为alpha+beta+噪声
v13: MA扫描 → 移动平均信号扫描
v14: 频率扫描 → 调仓频率最优解
v15: 多因子合成 → 等权→IC加权→ML加权
v16: 诊断 → 策略归因诊断
v17: 趋势 → 趋势/反转双模
v18: All-A → 全A股选股
v19: ETF轮动 → 行业ETF轮动
v20: 风格轮动 → 科技ETF vs 低波选股动态切换
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List, Callable


class StrategyTemplate:
    def __init__(self, name: str, version: str, description: str,
                 factors: List[str], rules: Dict[str, object],
                 backtest_params: Dict[str, object]):
        self.name = name
        self.version = version
        self.description = description
        self.factors = factors
        self.rules = rules
        self.backtest_params = backtest_params

    def __repr__(self):
        return f"StrategyTemplate(name={self.name}, version={self.version})"


PHOENIX_TEMPLATES = {
    "v20_style_rotation": StrategyTemplate(
        name="风格轮动策略",
        version="v20",
        description="月频动态切换：科技趋势向上→持有科技ETF，向下→退回低波选股",
        factors=["low_vol", "rev_1m", "amount_20d"],
        rules={
            "tech_ma_period": 60,
            "stock_top_n": 50,
            "use_stock_ma250": True,
            "use_stop_loss": True,
            "stop_loss_pct": 0.08,
            "market_bull_threshold": 0.0,
        },
        backtest_params={
            "rebalance_freq": "monthly",
            "cost_model": "30bp",
            "universe": "全A股",
        },
    ),
    "v19_etf_rotation": StrategyTemplate(
        name="ETF行业轮动",
        version="v19",
        description="基于行业动量的ETF轮动策略",
        factors=["momentum_1m", "momentum_3m", "volatility_1m"],
        rules={
            "top_n": 3,
            "rebalance_freq": 21,
            "ma_filter": 250,
        },
        backtest_params={
            "rebalance_freq": "monthly",
            "cost_model": "50bp",
            "universe": "ETF池",
        },
    ),
    "v18_all_a": StrategyTemplate(
        name="全A股低波反转",
        version="v18",
        description="全A股范围内的低波动率+反转策略",
        factors=["low_vol", "rev_1m", "amplitude"],
        rules={
            "top_n": 50,
            "ma250_filter": True,
            "liquidity_threshold": 50e6,
            "stop_loss_pct": 0.08,
        },
        backtest_params={
            "rebalance_freq": "monthly",
            "cost_model": "30bp",
            "universe": "全A股",
        },
    ),
    "v17_trend": StrategyTemplate(
        name="趋势反转双模",
        version="v17",
        description="根据市场状态切换趋势/反转模式",
        factors=["momentum_1m", "rev_1w", "volatility_1m", "ma_signal"],
        rules={
            "trend_threshold": 0.3,
            "regime_lookback": 60,
            "top_n": 30,
        },
        backtest_params={
            "rebalance_freq": "weekly",
            "cost_model": "30bp",
            "universe": "沪深300",
        },
    ),
    "v16_diag": StrategyTemplate(
        name="因子诊断策略",
        version="v16",
        description="包含因子alpha诊断的低波深挖策略",
        factors=["low_vol", "mom_1m", "rev_1w", "low_beta", "stability", "amplitude"],
        rules={
            "top_n": 30,
            "ma250_filter": True,
            "t_plus_1": True,
            "use_cost": True,
        },
        backtest_params={
            "rebalance_freq": "monthly",
            "cost_model": "30bp",
            "universe": "全A股",
        },
    ),
    "v15_multifactor": StrategyTemplate(
        name="多因子合成",
        version="v15",
        description="IC加权多因子策略",
        factors=["mom_1m", "rev_1w", "low_vol", "low_beta", "stability", "amplitude"],
        rules={
            "top_n": 30,
            "weight_method": "ic_weighted",
            "lookback_days": 365,
        },
        backtest_params={
            "rebalance_freq": "monthly",
            "cost_model": "30bp",
            "universe": "沪深300",
        },
    ),
    "v13_ma_scan": StrategyTemplate(
        name="均线扫描策略",
        version="v13",
        description="多均线组合扫描策略",
        factors=["ma_signal"],
        rules={
            "ma_fast_windows": [5, 10, 20, 30, 60],
            "ma_slow_window": 250,
            "top_n": 30,
        },
        backtest_params={
            "rebalance_freq": "daily",
            "cost_model": "30bp",
            "universe": "沪深300",
        },
    ),
    "v10_basic": StrategyTemplate(
        name="基础多因子",
        version="v10",
        description="基础多因子选股策略",
        factors=["ret_1m", "volatility_1m", "bb_position", "illiquidity"],
        rules={
            "top_n": 10,
            "ma_filter": 250,
        },
        backtest_params={
            "rebalance_freq": "monthly",
            "cost_model": "30bp",
            "universe": "创业板",
        },
    ),
}


def get_template(version: str) -> StrategyTemplate | None:
    return PHOENIX_TEMPLATES.get(version)


def list_templates() -> List[Dict[str, object]]:
    result = []
    for key, template in PHOENIX_TEMPLATES.items():
        result.append({
            "id": key,
            "name": template.name,
            "version": template.version,
            "description": template.description,
            "factors": template.factors,
            "rules": template.rules,
            "backtest_params": template.backtest_params,
        })
    return result


def apply_template(df: pd.DataFrame, template: StrategyTemplate,
                   factor_compute_fn: Callable) -> pd.DataFrame:
    factor_data = factor_compute_fn(df, template.factors)
    return factor_data


def template_docstring(template: StrategyTemplate) -> str:
    return f"""
{template.name} (v{template.version})
{template.description}

使用因子: {', '.join(template.factors)}

策略规则:
{chr(10).join([f"  - {k}: {v}" for k, v in template.rules.items()])}

回测参数:
{chr(10).join([f"  - {k}: {v}" for k, v in template.backtest_params.items()])}
"""


__all__ = ["StrategyTemplate", "PHOENIX_TEMPLATES", "get_template", "list_templates",
           "apply_template", "template_docstring"]
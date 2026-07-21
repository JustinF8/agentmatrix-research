from __future__ import annotations
import numpy as np
import pandas as pd
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


COMMISSION = 0.0003
STAMP_TAX = 0.0005
SLIPPAGE = 0.001
TRADE_COST = COMMISSION + SLIPPAGE
SELL_COST = COMMISSION + STAMP_TAX + SLIPPAGE


@dataclass
class TradeCosts:
    commission: float = COMMISSION
    stamp_tax: float = STAMP_TAX
    slippage: float = SLIPPAGE

    @property
    def buy_cost(self) -> float:
        return self.commission + self.slippage

    @property
    def sell_cost(self) -> float:
        return self.commission + self.stamp_tax + self.slippage


@dataclass
class BacktestResult:
    nav_history: pd.Series
    benchmark_nav: Optional[pd.Series] = None
    holdings: List[Dict] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)


def calculate_transaction_cost(turnover: float, costs: TradeCosts = None) -> float:
    costs = costs or TradeCosts()
    return turnover * (costs.buy_cost + costs.sell_cost)


def calculate_turnover(old_holdings: List[str], new_holdings: List[str]) -> float:
    old_set, new_set = set(old_holdings), set(new_holdings)
    if not old_set and not new_set:
        return 0.0
    total = max(len(old_set), len(new_set))
    if total == 0:
        return 0.0
    changes = len(new_set - old_set) + len(old_set - new_set)
    return changes / (2 * total)


def find_rebalance_dates(dates: pd.DatetimeIndex, start_date: str = "2020-01-01",
                         frequency: str = "semi-annual") -> pd.DatetimeIndex:
    df_dates = pd.DataFrame({"date": dates})
    df_dates["year"] = df_dates["date"].dt.year
    df_dates["month"] = df_dates["date"].dt.month

    if frequency == "semi-annual":
        rebalance_mask = df_dates["month"].isin([6, 12])
        rebalance_mask |= (df_dates["date"] == df_dates["date"].min())
        rebalance_mask |= (df_dates["date"] == df_dates["date"].max())
    elif frequency == "quarterly":
        rebalance_mask = df_dates["month"].isin([3, 6, 9, 12])
        rebalance_mask |= (df_dates["date"] == df_dates["date"].min())
        rebalance_mask |= (df_dates["date"] == df_dates["date"].max())
    elif frequency == "monthly":
        rebalance_mask = df_dates.groupby(["year", "month"]).tail(1)["date"].isin(dates)
    else:
        rebalance_mask = pd.Series([True] * len(dates), index=dates)

    rebal_dates = df_dates.loc[rebalance_mask & (df_dates["date"] >= start_date), "date"]
    return pd.DatetimeIndex(sorted(rebal_dates.unique()))


def run_backtest(prices: pd.DataFrame, factor_data: pd.DataFrame,
                 target_col: str = "factor", n_stocks: int = 10,
                 rebalance_frequency: str = "semi-annual",
                 costs: TradeCosts = None,
                 benchmark_prices: Optional[pd.DataFrame] = None) -> BacktestResult:
    costs = costs or TradeCosts()

    dates = sorted(prices.index.unique())
    rebal_dates = find_rebalance_dates(pd.DatetimeIndex(dates), frequency=rebalance_frequency)

    nav = 1.0
    bm_nav = 1.0
    nav_history = []
    bm_history = []
    all_dates = []
    holdings_log = []

    for i in range(1, len(rebal_dates)):
        s, e = rebal_dates[i-1], rebal_dates[i]

        mask = (factor_data["date"] >= s) & (factor_data["date"] <= e)
        period_data = factor_data.loc[mask]

        if period_data.empty:
            continue

        period_data["rank"] = period_data.groupby("date")[target_col].rank(pct=True)
        period_data["top_n"] = period_data["rank"] >= (1 - n_stocks / len(period_data["code"].unique()))

        top_stocks = period_data.loc[period_data["top_n"], "code"].unique()[:n_stocks]

        holdings_log.append({"date": s, "holdings": list(top_stocks)})

        seg_nav = 1.0
        seg_bm = 1.0

        start_idx = dates.index(s) if s in dates else 0
        end_idx = dates.index(e) if e in dates else len(dates) - 1

        for j in range(start_idx + 1, end_idx + 1):
            d = dates[j]

            stock_rets = []
            for code in top_stocks:
                if code in prices.columns:
                    prev_date = dates[j-1] if j > 0 else d
                    if prev_date in prices.index and d in prices.index:
                        prev_price = prices.loc[prev_date, code]
                        curr_price = prices.loc[d, code]
                        if prev_price > 0:
                            stock_rets.append(curr_price / prev_price - 1)

            dr = np.mean(stock_rets) if stock_rets else 0

            if j == start_idx + 1 and len(holdings_log) >= 2:
                prev_holdings = holdings_log[-2]["holdings"]
                turnover = calculate_turnover(prev_holdings, list(top_stocks))
                dr -= calculate_transaction_cost(turnover, costs)

            seg_nav *= (1 + dr)
            nav_history.append(nav * seg_nav)

            if benchmark_prices is not None:
                if d in benchmark_prices.index and prev_date in benchmark_prices.index:
                    prev_bm = benchmark_prices.loc[prev_date].iloc[0]
                    curr_bm = benchmark_prices.loc[d].iloc[0]
                    if prev_bm > 0:
                        br = curr_bm / prev_bm - 1
                    else:
                        br = 0
                else:
                    br = 0
                seg_bm *= (1 + br)
                bm_history.append(bm_nav * seg_bm)

            all_dates.append(d)

        nav *= seg_nav
        bm_nav *= seg_bm

    metrics = calculate_performance_metrics(nav_history, all_dates, bm_history)

    return BacktestResult(
        nav_history=pd.Series(nav_history, index=pd.DatetimeIndex(all_dates)),
        benchmark_nav=pd.Series(bm_history, index=pd.DatetimeIndex(all_dates)) if bm_history else None,
        holdings=holdings_log,
        metrics=metrics,
    )


def calculate_performance_metrics(nav_history: List[float], dates: List,
                                  bm_history: Optional[List[float]] = None) -> Dict:
    if not nav_history:
        return {}

    strategy_days = len(nav_history) if len(nav_history) > 0 else 252
    total_ret = (nav_history[-1] / nav_history[0] - 1) * 100
    ann_ret = (nav_history[-1] / nav_history[0]) ** (252 / strategy_days) - 1
    ann_ret_pct = ann_ret * 100

    daily_rets = [nav_history[i] / nav_history[i-1] - 1 for i in range(1, len(nav_history))]
    if daily_rets:
        avg_daily = np.mean(daily_rets)
        std_daily = np.std(daily_rets)
        sharpe = avg_daily / std_daily * math.sqrt(252) if std_daily > 0 else 0
        ann_vol = std_daily * math.sqrt(252) * 100
    else:
        sharpe = 0
        ann_vol = 0

    peak = 1.0
    mdd = 0.0
    mdd_start = 0
    mdd_end = 0
    peak_idx = 0
    current_dd_start = 0

    for j, n in enumerate(nav_history):
        if n > peak:
            peak = n
            peak_idx = j
            current_dd_start = j
        dd = (peak - n) / peak
        if dd > mdd:
            mdd = dd
            mdd_start = current_dd_start
            mdd_end = j

    mdd_pct = mdd * 100
    calmar = ann_ret_pct / mdd_pct if mdd > 0 else 0

    max_no_high = 0
    peak2 = nav_history[0]
    current_start = 0
    no_high_start = 0
    no_high_end = 0

    for j, n in enumerate(nav_history):
        if n >= peak2:
            peak2 = n
            current_start = j
        gap = j - current_start
        if gap > max_no_high:
            max_no_high = gap
            no_high_start = current_start
            no_high_end = j

    days_since_peak = len(nav_history) - 1 - peak_idx if peak_idx < len(nav_history) else 0
    latest_rtn = daily_rets[-1] * 100 if daily_rets else 0

    bm_total_ret = 0
    bm_ann_ret = 0
    if bm_history and len(bm_history) == len(nav_history):
        bm_total_ret = (bm_history[-1] / bm_history[0] - 1) * 100
        bm_ann_ret = (bm_history[-1] / bm_history[0]) ** (252 / strategy_days) - 1

    result = {
        "total_return": round(total_ret, 2),
        "annual_return": round(ann_ret_pct, 2),
        "max_drawdown": round(mdd_pct, 2),
        "sharpe_ratio": round(sharpe, 2),
        "calmar_ratio": round(calmar, 2),
        "annual_volatility": round(ann_vol, 2),
        "max_high_gap_days": max_no_high,
        "days_since_last_peak": days_since_peak,
        "latest_daily_return": round(latest_rtn, 2),
        "n_trading_days": strategy_days,
        "start_date": dates[0] if dates else "",
        "end_date": dates[-1] if dates else "",
        "benchmark_total_return": round(bm_total_ret, 2),
        "benchmark_annual_return": round(bm_ann_ret * 100, 2),
    }

    return result


def generate_nav_output(nav_history: pd.Series, mdd_period: Optional[Tuple[int, int]] = None,
                        sample_interval: int = 5) -> List[Dict]:
    nav_out = []
    mdd_range = set(range(mdd_period[0], mdd_period[1] + 1)) if mdd_period else set()

    for j in range(len(nav_history)):
        if j % sample_interval == 0 or j in mdd_range:
            nav_out.append({
                "date": str(nav_history.index[j].date()),
                "nav": round(nav_history.iloc[j], 4),
                "in_drawdown": j in mdd_range,
            })

    return nav_out

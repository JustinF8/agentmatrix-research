from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class FactorWeight:
    factor_name: str
    weight: float
    decay_score: float
    is_active: bool


@dataclass
class MultifactorResult:
    combined_factor: pd.Series
    weights: List[FactorWeight]
    ic_history: pd.Series
    decay_info: Dict = field(default_factory=dict)
    turnover: float = 0.0


def rolling_ic_weight(factor_data: pd.DataFrame, factor_cols: List[str],
                      target_col: str = "ret", window: int = 60,
                      min_periods: int = 20) -> pd.DataFrame:
    n_dates = len(factor_data["date"].unique())
    dates = sorted(factor_data["date"].unique())
    weights = pd.DataFrame(index=dates, columns=factor_cols)

    for i in range(n_dates):
        end = i
        start = max(0, i - window + 1)
        if end - start + 1 < min_periods:
            weights.iloc[i] = 1.0 / len(factor_cols)
            continue

        window_dates = dates[start:end + 1]
        window_data = factor_data[factor_data["date"].isin(window_dates)]

        ic_values = {}
        for col in factor_cols:
            if col not in window_data.columns:
                ic_values[col] = 0
                continue
            valid = window_data.dropna(subset=[col, target_col])
            if len(valid) < 20:
                ic_values[col] = 0
                continue
            ic = valid.groupby("date").apply(
                lambda x: x[col].corr(x[target_col]) if len(x) > 1 else np.nan
            ).mean()
            ic_values[col] = ic

        total_ic = sum(abs(v) for v in ic_values.values())
        if total_ic > 0:
            weights.iloc[i] = [abs(ic_values[col]) / total_ic for col in factor_cols]
        else:
            weights.iloc[i] = 1.0 / len(factor_cols)

    weights = weights.fillna(1.0 / len(factor_cols))
    return weights


def detect_factor_decay(factor_data: pd.DataFrame, factor_cols: List[str],
                        target_col: str = "ret", recent_window: int = 20,
                        full_window: int = 120, decay_threshold: float = 0.5) -> Dict[str, bool]:
    dates = sorted(factor_data["date"].unique())
    n_dates = len(dates)

    decay_status = {}
    for col in factor_cols:
        if col not in factor_data.columns:
            decay_status[col] = True
            continue

        recent_start = max(0, n_dates - recent_window)
        full_start = max(0, n_dates - full_window)

        recent_dates = dates[recent_start:]
        full_dates = dates[full_start:]

        recent_data = factor_data[factor_data["date"].isin(recent_dates)].dropna(subset=[col, target_col])
        full_data = factor_data[factor_data["date"].isin(full_dates)].dropna(subset=[col, target_col])

        recent_ic = recent_data.groupby("date").apply(
            lambda x: x[col].corr(x[target_col]) if len(x) > 1 else np.nan
        ).mean() if len(recent_data) > 0 else 0

        full_ic = full_data.groupby("date").apply(
            lambda x: x[col].corr(x[target_col]) if len(x) > 1 else np.nan
        ).mean() if len(full_data) > 0 else 0

        decay_ratio = abs(recent_ic) / abs(full_ic) if abs(full_ic) > 0 else 0
        decay_status[col] = decay_ratio < decay_threshold

    return decay_status


def greedy_forward_selection(factor_data: pd.DataFrame, factor_cols: List[str],
                             target_col: str = "ret", max_factors: int = 5,
                             min_ic_improvement: float = 0.01) -> List[str]:
    remaining = list(factor_cols)
    selected = []

    for _ in range(max_factors):
        best_ic = -1
        best_factor = None

        for factor in remaining:
            temp_factors = selected + [factor]
            if any(f not in factor_data.columns for f in temp_factors):
                continue

            combined = factor_data[temp_factors].mean(axis=1)
            valid = factor_data.dropna(subset=[target_col]).copy()
            valid["combined"] = combined

            ic = valid.groupby("date").apply(
                lambda x: x["combined"].corr(x[target_col]) if len(x) > 1 else np.nan
            ).mean()

            if ic > best_ic:
                best_ic = ic
                best_factor = factor

        if best_factor is not None and best_ic > min_ic_improvement:
            selected.append(best_factor)
            remaining.remove(best_factor)
        else:
            break

    return selected


def combine_factors(factor_data: pd.DataFrame, factor_cols: List[str],
                    weights: Optional[pd.DataFrame] = None,
                    normalize: bool = True) -> pd.Series:
    df = factor_data.copy()
    for col in factor_cols:
        if col not in df.columns:
            df[col] = 0

    if weights is None:
        combined = df[factor_cols].mean(axis=1)
    else:
        merged = df.merge(weights.reset_index().rename(columns={"index": "date"}),
                          on="date", how="left")
        merged = merged.fillna(1.0 / len(factor_cols))

        weighted_sum = np.zeros(len(merged))
        for col in factor_cols:
            weighted_sum += merged[col].values * merged.get(col + "_weight", 1.0 / len(factor_cols)).values
        combined = pd.Series(weighted_sum, index=df.index)

    if normalize:
        combined = combined.groupby(df["date"]).rank(pct=True)

    return combined


def multifactor_synthesis(factor_data: pd.DataFrame, factor_cols: List[str],
                          target_col: str = "ret", window: int = 60,
                          decay_threshold: float = 0.5, max_factors: int = 5,
                          **kwargs) -> MultifactorResult:
    df = factor_data.sort_values(["date", "code"]).copy()
    df["ret"] = df.groupby("code")["close"].pct_change(kwargs.get("hold_days", 5))

    weights_df = rolling_ic_weight(df, factor_cols, target_col, window)

    decay_status = detect_factor_decay(df, factor_cols, target_col,
                                       kwargs.get("recent_window", 20),
                                       kwargs.get("full_window", 120),
                                       decay_threshold)

    active_factors = [f for f in factor_cols if not decay_status.get(f, False)]
    if len(active_factors) > max_factors:
        active_factors = greedy_forward_selection(df, active_factors,
                                                  target_col, max_factors)

    weights_list = []
    for factor in factor_cols:
        avg_weight = weights_df[factor].mean() if factor in weights_df.columns else 0
        weights_list.append(FactorWeight(
            factor_name=factor,
            weight=avg_weight if factor in active_factors else 0,
            decay_score=1 - (1 if decay_status.get(factor, False) else 0),
            is_active=factor in active_factors,
        ))

    weights_list = sorted(weights_list, key=lambda x: x.weight, reverse=True)

    combined = combine_factors(df, active_factors)
    df["combined_factor"] = combined

    ic_history = df.groupby("date").apply(
        lambda x: x["combined_factor"].corr(x[target_col]) if len(x) > 1 else np.nan
    )

    turnover = _compute_turnover(df, "combined_factor")

    return MultifactorResult(
        combined_factor=combined,
        weights=weights_list,
        ic_history=ic_history,
        decay_info=decay_status,
        turnover=turnover,
    )


def _compute_turnover(df: pd.DataFrame, factor_col: str) -> float:
    df_sorted = df.sort_values(["code", "date"]).copy()
    df_sorted["rank"] = df_sorted.groupby("date")[factor_col].rank(pct=True)
    df_sorted["rank_prev"] = df_sorted.groupby("code")["rank"].shift(1)
    df_sorted = df_sorted.dropna(subset=["rank", "rank_prev"])

    df_sorted["top20"] = (df_sorted["rank"] >= 0.8).astype(int)
    df_sorted["top20_prev"] = (df_sorted["rank_prev"] >= 0.8).astype(int)
    df_sorted["bottom20"] = (df_sorted["rank"] <= 0.2).astype(int)
    df_sorted["bottom20_prev"] = (df_sorted["rank_prev"] <= 0.2).astype(int)

    churn_top = (df_sorted["top20"] != df_sorted["top20_prev"]).mean()
    churn_bottom = (df_sorted["bottom20"] != df_sorted["bottom20_prev"]).mean()

    return float((churn_top + churn_bottom) / 2)


def evaluate_multifactor(result: MultifactorResult, factor_data: pd.DataFrame,
                         target_col: str = "ret") -> Dict:
    df = factor_data.copy()
    df["combined_factor"] = result.combined_factor

    valid = df.dropna(subset=["combined_factor", target_col])

    ic = valid.groupby("date").apply(
        lambda x: x["combined_factor"].corr(x[target_col]) if len(x) > 1 else np.nan
    )
    rank_ic = valid.groupby("date").apply(
        lambda x: x["combined_factor"].corr(x[target_col], method="spearman") if len(x) > 1 else np.nan
    )

    df["rank"] = df.groupby("date")["combined_factor"].rank(pct=True)
    df["long"] = (df["rank"] >= 0.9).astype(int)
    df["short"] = (df["rank"] <= 0.1).astype(int)
    df["pnl"] = df["long"] * df[target_col] - df["short"] * df[target_col]

    daily_pnl = df.groupby("date")["pnl"].mean()
    cum_pnl = (1 + daily_pnl).cumprod()

    n_days = len(daily_pnl)
    annual_return = (cum_pnl.iloc[-1] / cum_pnl.iloc[0]) ** (250 / n_days) - 1 if n_days > 0 else 0
    sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(250) if daily_pnl.std() > 0 else 0

    return {
        "mean_ic": ic.mean(),
        "mean_rank_ic": rank_ic.mean(),
        "ic_std": ic.std(),
        "icir": ic.mean() / ic.std() if ic.std() > 0 else 0,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": (cum_pnl / cum_pnl.cummax() - 1).min(),
        "turnover": result.turnover,
        "active_factors": [w.factor_name for w in result.weights if w.is_active],
        "weights": {w.factor_name: w.weight for w in result.weights},
    }

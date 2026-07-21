from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .ic_bootstrap import ic_bootstrap_ci, ic_t_statistic

VERIFICATION_LEVELS = [
    "ic_stability",
    "oos_retention",
    "cost_resilience",
    "market_cap_neutral",
    "market_segments",
    "turnover_reasonable",
    "strategy_reproduce",
]


@dataclass
class VerificationResult:
    level: str
    passed: bool
    score: float
    details: Dict = field(default_factory=dict)
    threshold: Optional[float] = None


@dataclass
class VerificationReport:
    factor_name: str
    results: List[VerificationResult]
    overall_status: str
    overall_score: float
    summary: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "factor_name": self.factor_name,
            "overall_status": self.overall_status,
            "overall_score": self.overall_score,
            "summary": self.summary,
            "levels": [{
                "level": r.level,
                "passed": r.passed,
                "score": r.score,
                "threshold": r.threshold,
                "details": r.details,
            } for r in self.results]
        }


def verify_ic_stability(ic_values: pd.Series, n_boot: int = 1000) -> VerificationResult:
    mean_ic, t_stat = ic_t_statistic(ic_values)
    lower, upper = ic_bootstrap_ci(ic_values, n_boot=n_boot)
    passed = not (lower < 0 < upper)
    return VerificationResult(
        level="ic_stability",
        passed=passed,
        score=abs(mean_ic),
        threshold=0.0,
        details={
            "mean_ic": mean_ic,
            "t_stat": t_stat,
            "bootstrap_lower": lower,
            "bootstrap_upper": upper,
            "ic_count": len(ic_values.dropna()),
            "bootstrap_n": n_boot,
        }
    )


def verify_oos_retention(ic_in_sample: pd.Series, ic_out_sample: pd.Series,
                         threshold: float = 0.7) -> VerificationResult:
    mean_in = ic_in_sample.dropna().mean()
    mean_out = ic_out_sample.dropna().mean()
    retention = abs(mean_out) / abs(mean_in) if abs(mean_in) > 0 else 0
    passed = retention >= threshold
    return VerificationResult(
        level="oos_retention",
        passed=passed,
        score=retention,
        threshold=threshold,
        details={
            "in_sample_ic": mean_in,
            "out_sample_ic": mean_out,
            "retention_ratio": retention,
            "in_sample_count": len(ic_in_sample.dropna()),
            "out_sample_count": len(ic_out_sample.dropna()),
        }
    )


def verify_cost_resilience(factor_data: pd.DataFrame, cost_bps: float = 30,
                           hold_days: int = 5) -> VerificationResult:
    df = factor_data.copy().sort_values(["code", "date"])
    df["ret"] = df.groupby("code")["close"].pct_change(hold_days)
    df = df.dropna(subset=["factor", "ret"])
    if len(df) == 0:
        return VerificationResult(level="cost_resilience", passed=False, score=0,
                                  threshold=0.5, details={"error": "no valid data"})

    df["rank"] = df.groupby("date")["factor"].rank(pct=True)
    df["long"] = (df["rank"] >= 0.9).astype(int)
    df["short"] = (df["rank"] <= 0.1).astype(int)
    df["pnl"] = df["long"] * df["ret"] - df["short"] * df["ret"]

    cost_factor = cost_bps / 10000 * 2
    daily_cost = (df["long"] + df["short"]).sum() / len(df["code"].unique()) * cost_factor
    df["pnl_after_cost"] = df["pnl"] - cost_factor

    ic_before = df.groupby("date").apply(
        lambda x: x["factor"].corr(x["ret"]) if len(x) > 1 else np.nan
    ).mean()
    ic_after = df.groupby("date").apply(
        lambda x: x["factor"].corr(x["pnl_after_cost"]) if len(x) > 1 else np.nan
    ).mean()

    resilience = abs(ic_after) / abs(ic_before) if abs(ic_before) > 0 else 0
    passed = resilience >= 0.5
    return VerificationResult(
        level="cost_resilience",
        passed=passed,
        score=resilience,
        threshold=0.5,
        details={
            "ic_before_cost": ic_before,
            "ic_after_cost": ic_after,
            "resilience_ratio": resilience,
            "cost_bps": cost_bps,
            "hold_days": hold_days,
        }
    )


def verify_market_cap_neutral(factor_data: pd.DataFrame, cap_col: str = "market_cap") -> VerificationResult:
    df = factor_data.dropna(subset=["factor", cap_col]).copy()
    if len(df) == 0:
        return VerificationResult(level="market_cap_neutral", passed=False, score=0,
                                  threshold=0.5, details={"error": "no valid data"})

    df["cap_rank"] = df.groupby("date")[cap_col].rank(pct=True)
    df["cap_decile"] = (df["cap_rank"] * 10).astype(int)

    decile_ics = []
    for decile, group in df.groupby("cap_decile"):
        ic = group.groupby("date").apply(
            lambda x: x["factor"].corr(x["ret"]) if len(x) > 1 else np.nan
        ).mean()
        decile_ics.append(ic)

    overall_ic = df.groupby("date").apply(
        lambda x: x["factor"].corr(x["ret"]) if len(x) > 1 else np.nan
    ).mean()
    decile_ic_mean = np.mean([abs(x) for x in decile_ics if not np.isnan(x)])

    neutral_score = decile_ic_mean / abs(overall_ic) if abs(overall_ic) > 0 else 0
    passed = neutral_score >= 0.5
    return VerificationResult(
        level="market_cap_neutral",
        passed=passed,
        score=neutral_score,
        threshold=0.5,
        details={
            "overall_ic": overall_ic,
            "decile_ic_mean": decile_ic_mean,
            "decile_ics": decile_ics,
            "n_deciles": len([x for x in decile_ics if not np.isnan(x)]),
        }
    )


def verify_market_segments(factor_data: pd.DataFrame, min_positive_segments: int = 3) -> VerificationResult:
    df = factor_data.dropna(subset=["factor", "ret"]).copy()
    if len(df) == 0:
        return VerificationResult(level="market_segments", passed=False, score=0,
                                  threshold=min_positive_segments, details={"error": "no valid data"})

    dates = sorted(df["date"].unique())
    n_dates = len(dates)
    if n_dates < 3:
        return VerificationResult(level="market_segments", passed=False, score=0,
                                  threshold=min_positive_segments, details={"error": "insufficient dates"})

    segment_size = n_dates // 3
    segments = [
        df[df["date"].isin(dates[:segment_size])],
        df[df["date"].isin(dates[segment_size:2 * segment_size])],
        df[df["date"].isin(dates[2 * segment_size:])],
    ]

    positive_segments = 0
    segment_ics = []
    for i, seg in enumerate(segments):
        ic = seg.groupby("date").apply(
            lambda x: x["factor"].corr(x["ret"]) if len(x) > 1 else np.nan
        ).mean()
        segment_ics.append(ic)
        if ic > 0:
            positive_segments += 1

    passed = positive_segments >= min_positive_segments
    return VerificationResult(
        level="market_segments",
        passed=passed,
        score=positive_segments,
        threshold=min_positive_segments,
        details={
            "segment_ics": segment_ics,
            "positive_segments": positive_segments,
            "total_segments": len(segments),
        }
    )


def verify_turnover_reasonable(factor_data: pd.DataFrame, max_turnover: float = 0.5) -> VerificationResult:
    df = factor_data.sort_values(["code", "date"]).copy()
    df["factor_prev"] = df.groupby("code")["factor"].shift(1)
    df = df.dropna(subset=["factor", "factor_prev"])

    if len(df) == 0:
        return VerificationResult(level="turnover_reasonable", passed=False, score=0,
                                  threshold=max_turnover, details={"error": "no valid data"})

    df["rank"] = df.groupby("date")["factor"].rank(pct=True)
    df["rank_prev"] = df.groupby("date")["factor_prev"].rank(pct=True)

    df["top10"] = (df["rank"] >= 0.9).astype(int)
    df["top10_prev"] = (df["rank_prev"] >= 0.9).astype(int)
    df["bottom10"] = (df["rank"] <= 0.1).astype(int)
    df["bottom10_prev"] = (df["rank_prev"] <= 0.1).astype(int)

    churn_top = (df["top10"] != df["top10_prev"]).mean()
    churn_bottom = (df["bottom10"] != df["bottom10_prev"]).mean()
    avg_churn = (churn_top + churn_bottom) / 2

    passed = avg_churn <= max_turnover
    return VerificationResult(
        level="turnover_reasonable",
        passed=passed,
        score=1 - avg_churn,
        threshold=1 - max_turnover,
        details={
            "top10_churn": churn_top,
            "bottom10_churn": churn_bottom,
            "average_churn": avg_churn,
            "max_allowed": max_turnover,
        }
    )


def verify_strategy_reproduce(factor_data: pd.DataFrame, min_annual_return: float = 0.10) -> VerificationResult:
    df = factor_data.dropna(subset=["factor", "ret"]).copy()
    if len(df) == 0:
        return VerificationResult(level="strategy_reproduce", passed=False, score=0,
                                  threshold=min_annual_return, details={"error": "no valid data"})

    df["rank"] = df.groupby("date")["factor"].rank(pct=True)
    df["long"] = (df["rank"] >= 0.9).astype(int)
    df["short"] = (df["rank"] <= 0.1).astype(int)
    df["pnl"] = df["long"] * df["ret"] - df["short"] * df["ret"]

    daily_pnl = df.groupby("date")["pnl"].mean()
    cum_pnl = (1 + daily_pnl).cumprod()

    n_days = len(daily_pnl)
    if n_days < 250:
        annual_return = np.nan
    else:
        annual_return = (cum_pnl.iloc[-1] / cum_pnl.iloc[0]) ** (250 / n_days) - 1

    passed = annual_return >= min_annual_return if not np.isnan(annual_return) else False
    return VerificationResult(
        level="strategy_reproduce",
        passed=passed,
        score=annual_return if not np.isnan(annual_return) else 0,
        threshold=min_annual_return,
        details={
            "annual_return": annual_return,
            "total_return": cum_pnl.iloc[-1] / cum_pnl.iloc[0] - 1 if len(cum_pnl) > 0 else 0,
            "n_trading_days": n_days,
            "sharpe_ratio": daily_pnl.mean() / daily_pnl.std() * np.sqrt(250) if daily_pnl.std() > 0 else 0,
        }
    )


def verify_single_factor(factor_name: str, factor_data: pd.DataFrame,
                         ic_values: pd.Series, ic_in_sample: Optional[pd.Series] = None,
                         ic_out_sample: Optional[pd.Series] = None,
                         **kwargs) -> VerificationReport:
    results = []

    results.append(verify_ic_stability(ic_values))

    if ic_in_sample is not None and ic_out_sample is not None:
        results.append(verify_oos_retention(ic_in_sample, ic_out_sample))
    else:
        results.append(VerificationResult(
            level="oos_retention", passed=False, score=0,
            details={"error": "in/out sample IC not provided"}
        ))

    if "close" in factor_data.columns:
        results.append(verify_cost_resilience(factor_data))
    else:
        results.append(VerificationResult(
            level="cost_resilience", passed=False, score=0,
            details={"error": "close price not provided"}
        ))

    if "market_cap" in factor_data.columns and "ret" in factor_data.columns:
        results.append(verify_market_cap_neutral(factor_data))
    else:
        results.append(VerificationResult(
            level="market_cap_neutral", passed=False, score=0,
            details={"error": "market_cap or ret not provided"}
        ))

    if "ret" in factor_data.columns:
        results.append(verify_market_segments(factor_data))
    else:
        results.append(VerificationResult(
            level="market_segments", passed=False, score=0,
            details={"error": "ret not provided"}
        ))

    results.append(verify_turnover_reasonable(factor_data))

    if "ret" in factor_data.columns:
        results.append(verify_strategy_reproduce(factor_data))
    else:
        results.append(VerificationResult(
            level="strategy_reproduce", passed=False, score=0,
            details={"error": "ret not provided"}
        ))

    passed_count = sum(1 for r in results if r.passed)
    overall_score = passed_count / len(results)
    overall_status = "PASS" if overall_score >= 0.7 else ("CAUTION" if overall_score >= 0.4 else "FAIL")

    summary = {
        "total_levels": len(results),
        "passed_levels": passed_count,
        "failed_levels": len(results) - passed_count,
        "overall_score": overall_score,
        "overall_status": overall_status,
    }

    return VerificationReport(
        factor_name=factor_name,
        results=results,
        overall_status=overall_status,
        overall_score=overall_score,
        summary=summary,
    )


def verify_all(factors_data: Dict[str, pd.DataFrame],
               factors_ic: Dict[str, pd.Series],
               factors_ic_split: Optional[Dict[str, Tuple[pd.Series, pd.Series]]] = None,
               **kwargs) -> Dict[str, VerificationReport]:
    reports = {}
    for factor_name, data in factors_data.items():
        ic_values = factors_ic.get(factor_name, pd.Series())
        ic_in, ic_out = None, None
        if factors_ic_split and factor_name in factors_ic_split:
            ic_in, ic_out = factors_ic_split[factor_name]
        reports[factor_name] = verify_single_factor(
            factor_name, data, ic_values, ic_in, ic_out, **kwargs
        )
    return reports

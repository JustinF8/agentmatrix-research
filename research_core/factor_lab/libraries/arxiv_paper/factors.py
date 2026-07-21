from __future__ import annotations

import numpy as np
import pandas as pd

from research_core.factor_lab.operators import (
    cross_sectional_rank,
    ts_delta,
    ts_mean,
    ts_std,
)


IMPLEMENTED_ARXIV_FACTORS = (
    "arxiv_magnitude_shrink",
    "arxiv_lag3_reversal",
    "arxiv_bounce_proxy",
    "arxiv_residual_ma20",
    "arxiv_regime",
)


def _returns(df: pd.DataFrame) -> pd.Series:
    return df.groupby("code")["close"].pct_change()


def arxiv_magnitude_shrink(df: pd.DataFrame) -> pd.Series:
    ret_1d = _returns(df)
    abs_ret_lag = ret_1d.abs().shift(1)
    return -np.log1p(abs_ret_lag * 100)


def arxiv_lag3_reversal(df: pd.DataFrame) -> pd.Series:
    ret_3d = df.groupby("code")["close"].pct_change(3)
    return -ret_3d.shift(1)


def arxiv_bounce_proxy(df: pd.DataFrame) -> pd.Series:
    ret_1d = _returns(df)
    abs_ret_lag = ret_1d.abs().shift(1)
    return -abs_ret_lag * (abs_ret_lag > 0.02).astype(float)


def arxiv_residual_ma20(df: pd.DataFrame) -> pd.Series:
    close = df["close"]
    ma20 = ts_mean(df, "close", 20, min_periods=20)
    residual_20 = (close - ma20) / close
    return -residual_20


def arxiv_regime(df: pd.DataFrame) -> pd.Series:
    ret_1d = _returns(df)
    vol_20 = ts_std(df.assign(ret_1d=ret_1d), "ret_1d", 20, min_periods=20)
    vol_60 = ts_std(df.assign(ret_1d=ret_1d), "ret_1d", 60, min_periods=60)
    regime_score = (vol_20 / vol_60 - 1).replace([np.inf, -np.inf], 0)
    return -regime_score.clip(-1, 1)


_ARXIV_FACTOR_MAP = {
    "arxiv_magnitude_shrink": arxiv_magnitude_shrink,
    "arxiv_lag3_reversal": arxiv_lag3_reversal,
    "arxiv_bounce_proxy": arxiv_bounce_proxy,
    "arxiv_residual_ma20": arxiv_residual_ma20,
    "arxiv_regime": arxiv_regime,
}


def compute_arxiv_factors(df: pd.DataFrame, factor_names: list[str] | None = None) -> pd.DataFrame:
    if factor_names is None:
        factor_names = list(IMPLEMENTED_ARXIV_FACTORS)
    
    result = df[["code", "date"]].copy()
    for name in factor_names:
        if name in _ARXIV_FACTOR_MAP:
            result[name] = _ARXIV_FACTOR_MAP[name](df)
        else:
            raise ValueError(f"Unknown arxiv factor: {name}")
    return result
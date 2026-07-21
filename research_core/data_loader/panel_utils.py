from __future__ import annotations
import numpy as np
import pandas as pd


def add_date_index(df: pd.DataFrame) -> pd.DataFrame:
    all_dates = pd.Index(sorted(pd.to_datetime(df["date"]).unique()))
    pos = {d: i for i, d in enumerate(all_dates)}
    out = df.copy()
    out["di"] = pd.to_datetime(out["date"]).map(pos).astype("int64")
    return out


def forward_return(df: pd.DataFrame, hold: int, price_col: str = "close") -> pd.Series:
    d = df if "di" in df.columns else add_date_index(df)
    base = d[["code", "di", price_col]].copy()
    base = base.rename(columns={price_col: "_p_t"})
    look = d[["code", "di", price_col]].copy()
    look = look.rename(columns={price_col: "_p_fut", "di": "_di_src"})
    base["_di_tgt"] = base["di"] + hold
    merged = base.merge(
        look, left_on=["code", "_di_tgt"], right_on=["code", "_di_src"], how="left")
    fwd = merged["_p_fut"].values / merged["_p_t"].values - 1.0
    s = pd.Series(fwd, index=d.index)
    return s.replace([np.inf, -np.inf], np.nan)

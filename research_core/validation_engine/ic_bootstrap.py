from __future__ import annotations
import numpy as np
import pandas as pd


def ic_bootstrap_ci(ic_values: pd.Series, n_boot: int = 1000,
                     alpha: float = 0.05) -> tuple[float, float]:
    ic_arr = ic_values.dropna().values
    n = len(ic_arr)
    means = np.zeros(n_boot)
    for i in range(n_boot):
        idx = np.random.randint(0, n, size=n)
        means[i] = np.mean(ic_arr[idx])
    lower = np.percentile(means, alpha * 50)
    upper = np.percentile(means, 100 - alpha * 50)
    return float(lower), float(upper)


def ic_t_statistic(ic_values: pd.Series) -> tuple[float, float]:
    ic_arr = ic_values.dropna().values
    if len(ic_arr) < 2:
        return np.nan, np.nan
    mean_ic = np.mean(ic_arr)
    std_ic = np.std(ic_arr, ddof=1)
    n = len(ic_arr)
    t_stat = mean_ic / (std_ic / np.sqrt(n)) if std_ic > 0 else 0
    return float(mean_ic), float(t_stat)

"""
5日反转因子。

公式: (P_{t-5} - P_t) / P_{t-5}

短期反转效应：过去5日跌幅越大，预期未来收益越高。
"""
import pandas as pd


def compute(panel: pd.DataFrame) -> pd.Series:
    """计算 5 日反转因子值。

    Args:
        panel: DataFrame，必须包含 date, code, close 列

    Returns:
        pd.Series，因子值（5日反转收益率），长度与 panel 一致
    """
    panel_sorted = panel.sort_values(["code", "date"]).reset_index(drop=True)
    result = -panel_sorted.groupby("code")["close"].pct_change(5)

    result.index = panel_sorted.index
    return result.reindex(panel.index)
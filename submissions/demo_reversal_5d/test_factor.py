"""
5日反转因子单元测试。

验证：
1. 合成数据上的公式正确性
2. 边界情况不崩溃
"""
import unittest
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factor import compute


class TestReversal5d(unittest.TestCase):
    def test_basic_reversal(self):
        """用合成数据验证 5 日反转公式"""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        records = []
        base = 10.0
        for i, date in enumerate(dates):
            records.append({
                "date": date,
                "code": "000001",
                "close": base * (1 + i * 0.02),
                "open": base * (1 + i * 0.02),
                "high": base * (1 + i * 0.02) * 1.005,
                "low": base * (1 + i * 0.02) * 0.995,
                "volume": 1000000,
                "amount": 10000000,
            })

        panel = pd.DataFrame(records)
        result = compute(panel)

        self.assertTrue(result.iloc[:5].isna().all(),
                        f"前5天应为NaN，实际: {result.iloc[:5].tolist()}")

        expected = ((base * (1 + 0 * 0.02)) - (base * (1 + 5 * 0.02))) / (base * (1 + 0 * 0.02))
        actual = result.iloc[5]
        self.assertAlmostEqual(actual, expected, places=6,
                               msg=f"第6天因子值应为 {expected:.6f}，实际 {actual:.6f}")

    def test_multiple_stocks(self):
        """多只股票独立计算"""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        records = []
        for code, base in [("000001", 10.0), ("000002", 20.0)]:
            for i, date in enumerate(dates):
                records.append({
                    "date": date, "code": code,
                    "close": base * (1 + i * 0.02),
                    "open": base, "high": base * 1.01,
                    "low": base * 0.99, "volume": 1000000,
                    "amount": 10000000,
                })

        panel = pd.DataFrame(records)
        result = compute(panel)

        stock1 = result[panel["code"] == "000001"].reset_index(drop=True)
        stock2 = result[panel["code"] == "000002"].reset_index(drop=True)
        pd.testing.assert_series_equal(stock1, stock2, check_names=False,
                                       obj="两只股票的因子值应完全一致")

    def test_short_panel_no_crash(self):
        """数据不足一个窗口时不崩溃"""
        panel = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=3, freq="B"),
            "code": ["000001"] * 3,
            "close": [10.0, 10.1, 10.2],
            "open": [10.0] * 3,
            "high": [10.5] * 3,
            "low": [9.5] * 3,
            "volume": [1000000] * 3,
            "amount": [10000000] * 3,
        })

        result = compute(panel)
        self.assertEqual(len(result), 3)
        self.assertTrue(result.isna().all())


if __name__ == "__main__":
    unittest.main()
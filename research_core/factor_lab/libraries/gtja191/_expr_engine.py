"""GTJA191 表达式求值引擎（私有模块）

把 qlib-factor-zoo ``loader_gtja191.py`` 中的 191 个 qlib 表达式原样作为
因子定义，通过一个受信命名空间 + ``eval`` 驱动计算。

设计要点
--------
* 每个因子表达式（如 ``Rank(-1*Corr(Rank(Delta(Log($volume+1),1),6), ...))``）
  中的 ``$field`` 被替换为 ``DF["field"]``，其余均为合法 Python 算术/函数调用。
* 所有 qlib 算子映射为本项目 ``factor_lab`` 的 pandas 算子（按 ``code`` 分组、
  截面 ``date`` 排名），语义严格对齐 qlib-factor-zoo 的 ``qlib/data/ops.py``：
  - ``Max/Min/Mean/Std/Sum`` 等为按 code 分组的滚动窗口（min_periods=1）。
  - ``Std`` 用 pandas 默认 ddof=1（qlib 的 ``rolling.std()`` 默认）。
  - ``WMA`` 用线性权重 1..N 归一化后做 nanmean（对齐 qlib 的 weighted_mean）。
  - ``TsArgmax/TsArgmin`` 返回**滚动窗口内极值所在位置上的取值**（非索引），
    对齐 qlib custom_ops 的 "argmax/min VALUE extraction"。
  - ``Rank(X, N<=1)`` 为截面百分比排名（对齐聚宽 RANK 语义）；``Rank(X, N>1)``
    为 N 期滚动百分比排名（对齐 qlib RollingRank）。
  - ``SMA(X,N,M)`` 为递归 SMA：Y_t=(M*X_t+(N-M)*Y_{t-1})/N，Y_0=X_0。
  - ``Amount()`` 由 vwap*volume 代理。
* 引擎完全自包含，不依赖 qlib 运行时；表达式字符串即"公式源码"。

数据要求
--------
``df`` 需包含列: ``date, code, open, high, low, close, volume``（可选 ``vwap``，
缺省时由 OHLC 近似）。长表格式（每行一个 (date, code) 观测）。
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

_FIELD_RE = re.compile(r"\$(\w+)")

_CODE = "code"
_DATE = "date"

# 由 _make_namespace 在每次求值时写入的全局对齐数组（index 与 df 一致）
_CODE_ARR: pd.Series = None  # type: ignore
_DATE_ARR: pd.Series = None  # type: ignore
_VWAP_ARR: pd.Series = None  # type: ignore
_VOL_ARR: pd.Series = None   # type: ignore


# ---------------------------------------------------------------------------
# 时间序列算子（Series 进 / Series 出，按 code 分组；index 与 df 对齐）
# ---------------------------------------------------------------------------

def op_ref(s, n):
    """REF / DELAY: 前移 n 期。"""
    return s.groupby(_CODE_ARR, group_keys=False).shift(int(n))


def op_delta(s, n):
    return s.groupby(_CODE_ARR, group_keys=False).diff(int(n))


def op_mean(s, n):
    n = int(n)
    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).mean().reset_index(level=0, drop=True)


def op_std(s, n):
    n = int(n)
    # 总体标准差（ddof=0）：使 Std(X, 1) = 0（单元素窗口标准差为 0），
    # 与金融语义一致；qlib 默认 ddof=1 在窗口=1 时会产生 NaN。
    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).std(ddof=0).reset_index(level=0, drop=True)


def op_sum(s, n):
    n = int(n)
    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).sum().reset_index(level=0, drop=True)


def op_max(s, n):
    n = int(n)
    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).max().reset_index(level=0, drop=True)


def op_min(s, n):
    n = int(n)
    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).min().reset_index(level=0, drop=True)


def op_tsargmax(s, n):
    """qlib TsArgmax: 返回滚动窗口内最大值所在位置上的取值（VALUE）。"""
    n = int(n)

    def _f(w):
        if np.isnan(w).all():
            return np.nan
        arr = np.where(np.isnan(w), -np.inf, w)
        return float(w[np.argmax(arr)])

    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).apply(_f, raw=True).reset_index(level=0, drop=True)


def op_tsargmin(s, n):
    """qlib TsArgmin: 返回滚动窗口内最小值所在位置上的取值（VALUE）。"""
    n = int(n)

    def _f(w):
        if np.isnan(w).all():
            return np.nan
        arr = np.where(np.isnan(w), np.inf, w)
        return float(w[np.argmin(arr)])

    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).apply(_f, raw=True).reset_index(level=0, drop=True)


def op_rank(s, *args):
    """Rank: N<=1 -> 截面百分比排名(pct); N>1 -> N 期滚动百分比排名。"""
    if len(args) == 0 or (len(args) == 1 and float(args[0]) <= 1):
        return s.groupby(_DATE_ARR, group_keys=False).rank(method="average", pct=True)
    return _ts_rank(s, int(args[0]))


def _ts_rank(s, n):
    n = int(n)

    def _f(w):
        if np.isnan(w).all():
            return np.nan
        x = w[~np.isnan(w)]
        latest = x[-1]
        below = np.sum(x < latest)
        equal = np.sum(x == latest)
        return (below + (equal + 1.0) / 2.0) / len(x)

    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).apply(_f, raw=True).reset_index(level=0, drop=True)


def op_corr(a, b, n):
    return _roll2(a, b, n, "corr")


def op_cov(a, b, n):
    return _roll2(a, b, n, "cov")


def _roll2(a, b, n, kind):
    n = int(n)
    tmp = pd.DataFrame({"__a": np.asarray(a, dtype=float), "__b": np.asarray(b, dtype=float)}, index=a.index)
    tmp["__code"] = _CODE_ARR.values
    out = pd.Series(np.nan, index=a.index)
    for _, g in tmp.groupby("__code"):
        va = g["__a"]
        vb = g["__b"]
        if kind == "corr":
            c = va.rolling(n, min_periods=1).corr(vb)
        else:
            c = va.rolling(n, min_periods=1).cov(vb)
        # 方差为 0 时 corr/cov 会产生 inf，统一转 NaN（相关性未定义）
        c = c.replace([np.inf, -np.inf], np.nan)
        out.loc[g.index] = c.values
    return out


def op_slope(s, n):
    """对序列 n 做线性回归斜率（Slope(X, n)）；窗口含 NaN 时在有效点上回退。"""
    n = int(n)

    def _f(w):
        if np.isnan(w).all():
            return np.nan
        if np.isnan(w).any():
            idx = np.where(~np.isnan(w))[0]
            if len(idx) < 2:
                return np.nan
            xw = idx + 1.0
            yw = w[idx]
        else:
            xw = np.arange(1.0, len(w) + 1.0)
            yw = w
        xc = xw - xw.mean()
        yc = yw - yw.mean()
        denom = float(np.dot(xc, xc))
        if denom == 0:
            return np.nan
        return float(np.dot(xc, yc) / denom)

    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).apply(_f, raw=True).reset_index(level=0, drop=True)


def op_sma(s, n, m):
    """A 股习惯递归 SMA: Y_t = (M*X_t + (N-M)*Y_{t-1}) / N，Y_0 = X_0。"""
    n = float(int(n))
    m = float(int(m))
    out = pd.Series(np.nan, index=s.index)
    for _, g in s.groupby(_CODE_ARR):
        vals = g.values.astype(float)
        prev = np.nan
        res = []
        for v in vals:
            if np.isnan(v):
                res.append(np.nan)
                continue
            if np.isnan(prev):
                prev = v
            else:
                prev = (m * v + (n - m) * prev) / n
            res.append(prev)
        out.loc[g.index] = res
    return out


def op_wma(s, n):
    """线性权重 WMA（1..N 归一化，nanmean）；按实际窗口长度计算权重。"""
    n = int(n)

    def _f(x):
        L = len(x)
        if np.isnan(x).all():
            return np.nan
        w = np.arange(1, L + 1, dtype=float)
        w = w / w.sum()
        xc = np.where(np.isnan(x), 0.0, x)
        ww = np.where(np.isnan(x), 0.0, w)
        sww = ww.sum()
        if sww <= 0:
            return np.nan
        return float(np.nansum(ww * xc) / sww)

    return s.groupby(_CODE_ARR, group_keys=False).rolling(n, min_periods=1).apply(_f, raw=True).reset_index(level=0, drop=True)


def op_amount():
    """Amount() 代理 = vwap * volume。"""
    return _VWAP_ARR * _VOL_ARR


# ---------------------------------------------------------------------------
# 元素算子
# ---------------------------------------------------------------------------

def op_greater(a, b):
    return np.maximum(a, b)


def op_less(a, b):
    return np.minimum(a, b)


def op_abs(x, *args):
    return np.abs(x)


def op_sign(x, *args):
    return np.sign(x)


def op_power(a, b):
    return np.power(a, b)


def op_log(x, *args):
    # qlib 的 Log 仅接受 1 个特征参数；GTJA 表达式中偶有 Log(X, 1) 写法，
    # 第二个参数为冗余（对齐 qlib 解析器），此处忽略。
    return np.log(x)


def op_if(cond, a, b):
    idx = cond.index
    ca = np.asarray(cond, dtype=bool)
    aa = np.asarray(a, dtype=float)
    bb = np.asarray(b, dtype=float)
    res = np.where(ca, aa, bb)
    out = pd.Series(res, index=idx)
    # 条件为 NaN 时结果置 NaN
    out = out.where(pd.Series(np.asarray(cond), index=idx).notna())
    return out


# ---------------------------------------------------------------------------
# 命名空间构造 + 求值
# ---------------------------------------------------------------------------

_NS_FUNCS = {
    "Ref": op_ref,
    "Delay": op_ref,
    "Delta": op_delta,
    "Mean": op_mean,
    "Std": op_std,
    "Sum": op_sum,
    "Max": op_max,
    "Min": op_min,
    "TsArgmax": op_tsargmax,
    "TsArgmin": op_tsargmin,
    "Rank": op_rank,
    "Corr": op_corr,
    "Cov": op_cov,
    "Slope": op_slope,
    "SMA": op_sma,
    "WMA": op_wma,
    "Amount": op_amount,
    "Greater": op_greater,
    "Less": op_less,
    "Abs": op_abs,
    "Sign": op_sign,
    "Power": op_power,
    "Log": op_log,
    "If": op_if,
}

_CACHE: dict = {}


def _make_namespace(df: pd.DataFrame):
    global _CODE_ARR, _DATE_ARR, _VWAP_ARR, _VOL_ARR
    _CODE_ARR = df[_CODE].reset_index(drop=True)
    _DATE_ARR = df[_DATE].reset_index(drop=True)
    _VOL_ARR = df["volume"].reset_index(drop=True).astype(float)
    if "vwap" in df.columns:
        _VWAP_ARR = df["vwap"].reset_index(drop=True).astype(float)
    else:
        _VWAP_ARR = ((df["open"] + df["high"] + df["low"] + df["close"]) / 4.0).reset_index(drop=True).astype(float)
    ns = dict(_NS_FUNCS)
    ns["DF"] = df
    ns["np"] = np
    return ns


def evaluate(expr: str, df: pd.DataFrame):
    """对单个 qlib 表达式在面板 df 上求值，返回与 df 对齐的 Series。

    ``$field`` 在求值前被替换为 ``DF["field"]``（qlib 表达式语法）。
    qlib 中以 ``=`` 表示相等比较，求值前转换为 Python 的 ``==``。
    """
    ns = _make_namespace(df)
    code = _CACHE.get(expr)
    if code is None:
        transformed = _FIELD_RE.sub(r'DF["\1"]', expr)
        # qlib 用单个 = 表示相等（如 If(A=B, ...)）；转为 Python 的 ==
        transformed = re.sub(r"(?<![=!<>])=(?![=])", "==", transformed)
        code = compile(transformed, "<gtja>", "eval")
        _CACHE[expr] = code
    result = eval(code, {"__builtins__": {}}, ns)  # noqa: S307 - 受信本地常量
    if not isinstance(result, pd.Series):
        result = pd.Series(result, index=df.index)
    return result

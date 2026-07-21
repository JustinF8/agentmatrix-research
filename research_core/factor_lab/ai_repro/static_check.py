from __future__ import annotations
import ast

_ALLOWED_BASE = {
    "compute_factor", "df", "data", "np", "numpy", "pd", "pandas",
    "groupby", "rolling", "shift", "rank", "mean", "std", "sum", "min", "max",
    "corr", "cov", "apply", "transform", "pct_change", "diff", "abs", "sign",
    "log", "sqrt", "where", "fillna", "reset_index", "assign", "values",
    "index", "Series", "DataFrame", "astype", "len", "range", "float", "int",
    "copy", "dropna", "cumprod", "cumsum", "cummax", "ffill", "bfill", "clip",
    "expanding", "ewm", "isna", "notna", "replace", "sort_values", "rename",
    "loc", "iloc", "to_numpy", "tolist", "nunique", "unique", "count", "median",
    "var", "skew", "kurt", "quantile", "first", "last", "head", "tail", "merge",
    "concat", "pivot", "stack", "unstack", "round", "zip", "list", "dict",
    "tuple", "set", "sorted", "map", "enumerate",
}


def check(translated_code: str, factor_source: str, helper_names: set[str]) -> dict:
    issues = []

    try:
        tree = ast.parse(translated_code)
    except SyntaxError as e:
        return {"status": "compile_failed", "issues": [f"SyntaxError: {e}"]}

    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "compute_factor" not in funcs:
        return {"status": "missing_compute_factor",
                "issues": ["No function compute_factor(df) defined."]}

    defined = set(funcs)
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
    known = _ALLOWED_BASE | helper_names | defined
    suspicious = sorted(c for c in called if c not in known and not c.startswith("_"))
    suspicious = [s for s in suspicious if s.isidentifier() and len(s) > 2]
    if suspicious:
        issues.append("Calls names not found among helpers/allowed: "
                      + ", ".join(suspicious[:12]))

    status = "need_review" if issues else "passed"
    return {"status": status, "issues": issues, "suspicious": suspicious}

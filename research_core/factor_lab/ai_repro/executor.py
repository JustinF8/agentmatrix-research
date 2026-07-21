from __future__ import annotations
import ast
import re

_KNOWN_NAMES = {
    "abs", "min", "max", "len", "range", "float", "int", "str", "list", "tuple",
    "set", "dict", "sorted", "enumerate", "zip", "map", "any", "all", "sum",
    "np", "log", "sign", "sqrt", "exp", "where", "minimum", "maximum", "isnan",
    "nan", "inf", "full", "arange", "dot", "prod", "argmax", "argmin", "power",
    "clip", "nanmean", "nanstd",
    "pd", "Series", "DataFrame", "assign", "groupby", "transform", "apply",
    "rolling", "shift", "diff", "pct_change", "replace", "fillna", "rank",
    "mean", "std", "sum", "cov", "corr", "sort_values", "reset_index", "to_numpy",
    "divide", "copy", "astype", "nunique", "abs", "iloc", "loc", "index",
    "columns", "values", "to_datetime", "concat",
}


def _rename_function(source: str, new_name: str = "compute_factor") -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    func = next((n for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if func is None or func.name == new_name:
        return source
    lines = source.splitlines()
    idx = func.lineno - 1
    lines[idx] = re.sub(rf"(def\s+){re.escape(func.name)}\b",
                        rf"\g<1>{new_name}", lines[idx], count=1)
    return "\n".join(lines)


def unresolved_helpers(factor_rec: dict, index: dict) -> list[str]:
    out = []
    for name in factor_rec.get("calls", []):
        if name in index:
            continue
        if name in _KNOWN_NAMES:
            continue
        if re.fullmatch(r"[a-z_][a-z0-9_]{2,}", name) and not name.startswith("__"):
            out.append(name)
    return sorted(set(out))


def extract(factor_rec: dict, helper_src: str) -> dict:
    src = factor_rec.get("source", "")
    final_code = _rename_function(src, "compute_factor")
    args = factor_rec.get("args", [])
    first_param = args[0] if args else "df"
    bundle = (helper_src.strip() + "\n\n\n" + final_code).strip() if helper_src else final_code
    return {
        "original_source": src,
        "final_code": final_code,
        "bundle": bundle,
        "first_param": first_param,
        "factor_name": factor_rec.get("unique_name", factor_rec.get("name", "")),
    }


SUMMARY_SYSTEM = (
    "You are a code-reading assistant. You explain what Python factor code does "
    "in plain language for a human reviewer. You NEVER rewrite, translate, "
    "optimize, refactor, or output code of any kind. You only describe what the "
    "given code already does, strictly based on what is written."
)

SUMMARY_TEMPLATE = """Explain, in plain language, exactly what the following quantitative factor code computes.

Rules:
- Describe it step by step, in the order the code executes.
- Refer to helper functions by name; state what each does based ONLY on the helper definitions provided below.
- Do NOT output any code, pseudocode, or formulas in code form.
- Do NOT suggest improvements or alternatives.
- Do NOT guess anything not present in the code.

Factor name: {factor_name}

Factor code (this is the ground truth — do not restate it as code):
{factor_source}

Helper / operator definitions (reference only):
{helper_src}

Now give a concise plain-language explanation in 5-10 sentences."""


def summarize(factor_rec: dict, helper_src: str, client_module,
              provider: str | None = None, cfg: dict | None = None) -> str:
    prompt = SUMMARY_TEMPLATE.format(
        factor_name=factor_rec.get("unique_name", factor_rec.get("name", "")),
        factor_source=factor_rec.get("source", ""),
        helper_src=(helper_src or "(none)")[:12000],
    )
    return client_module.chat(prompt, system=SUMMARY_SYSTEM,
                              provider=provider, temperature=0.0, cfg=cfg)

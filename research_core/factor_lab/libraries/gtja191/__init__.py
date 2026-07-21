"""GTJA191 (国泰君安 Alpha191) 因子库。"""
from __future__ import annotations

from research_core.factor_lab.libraries.gtja191.factors import (
    GTJA_EXPRESSIONS,
    IMPLEMENTED_GTJA191_FACTORS,
    compute_gtja191_alphas,
    get_factor_names,
    get_factor_formula,
)
from research_core.factor_lab.libraries.gtja191.specs import (
    gtja191_specs,
    get_spec,
    get_all_specs,
)

__all__ = [
    "GTJA_EXPRESSIONS",
    "IMPLEMENTED_GTJA191_FACTORS",
    "compute_gtja191_alphas",
    "get_factor_names",
    "get_factor_formula",
    "gtja191_specs",
    "get_spec",
    "get_all_specs",
]

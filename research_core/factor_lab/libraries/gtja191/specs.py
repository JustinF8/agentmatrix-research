"""GTJA191 因子规格（每因子的公式源码与元信息）。

``gtja191_specs()`` 返回全部 191 个因子的 ``FactorResearchSpec`` 列表，
公式严格还原自 qlib-factor-zoo 的 ``loader_gtja191.py``。
"""
from __future__ import annotations

import re

from contracts.factor_research import FactorResearchSpec, ValidationThreshold

from research_core.factor_lab.libraries.gtja191.factors import GTJA_EXPRESSIONS

GTJA191_SOURCE = "国泰君安短周期价量 Alpha191"
GTJA191_VERSION = "v2026.07"
GTJA191_COMMON_THRESHOLDS = [
    ValidationThreshold("formula_match_ratio", ">=", 1.0, "代码实现与规格书公式逐项一致。"),
    ValidationThreshold("field_mapping_match_ratio", ">=", 1.0, "字段、复权、频率和股票池口径一致。"),
    ValidationThreshold("sample_point_error_ratio", "<=", 0.0, "抽样点位误差为零。"),
    ValidationThreshold("cross_section_spearman", ">=", 0.99, "与外部真值做截面对齐。"),
]

_KNOWN_FIELDS = ("open", "high", "low", "close", "volume", "vwap")


def _required_fields(expr: str) -> list[str]:
    """从因子表达式中提取所需行情字段。"""
    fields = set()
    for tok in re.findall(r"\$(\w+)", expr):
        if tok in _KNOWN_FIELDS:
            fields.add(tok)
    if "Amount(" in expr:
        fields.update(("vwap", "volume"))
    return sorted(fields)


def gtja191_specs() -> list[FactorResearchSpec]:
    """返回全部 191 个 GTJA191 因子的规格列表。"""
    specs: list[FactorResearchSpec] = []
    for idx in range(1, 192):
        name = f"alpha{idx}"
        expr = GTJA_EXPRESSIONS[name]
        specs.append(
            FactorResearchSpec(
                factor_name=name,
                library="GTJA191",
                version=GTJA191_VERSION,
                display_name=f"GTJA191 Alpha#{idx}",
                factor_id=f"gtja191_alpha_{idx:03d}",
                source_document=GTJA191_SOURCE,
                formula=str(expr),
                description=f"GTJA191 Alpha#{idx} 因子（qlib 表达式驱动实现）。",
                required_fields=_required_fields(expr),
                parameters={},
                validation_targets=GTJA191_COMMON_THRESHOLDS,
                tags=["gtja191", "price_volume", "implemented"],
                metadata={"status": "implemented", "implementation_stage": "factor_lab", "formula_source": "qlib-factor-zoo/loader_gtja191.py"},
            )
        )
    return specs


def get_spec(name: str) -> FactorResearchSpec | None:
    """返回单个因子规格（未找到返回 None）。"""
    for s in gtja191_specs():
        if s.factor_name == name:
            return s
    return None


def get_all_specs() -> dict[str, FactorResearchSpec]:
    """返回 factor_name -> spec 的字典。"""
    return {s.factor_name: s for s in gtja191_specs()}


__all__ = [
    "GTJA191_SOURCE",
    "GTJA191_VERSION",
    "GTJA191_COMMON_THRESHOLDS",
    "gtja191_specs",
    "get_spec",
    "get_all_specs",
]

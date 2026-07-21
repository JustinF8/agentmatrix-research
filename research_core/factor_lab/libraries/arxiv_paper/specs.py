from __future__ import annotations

from contracts.factor_research import FactorResearchSpec, ValidationThreshold


ARXIV_SOURCE = "arXiv Quantitative Finance Papers"
ARXIV_VERSION = "v2026.07"
ARXIV_COMMON_THRESHOLDS = [
    ValidationThreshold("formula_match_ratio", ">=", 1.0, "代码实现与论文公式一致。"),
    ValidationThreshold("field_mapping_match_ratio", ">=", 1.0, "字段映射与论文一致。"),
]


ARXIV_PAPERS = {
    "2606.29591": {
        "title": "The Bounce Has No Direction: Sign, Magnitude, and Microstructure of Equity Return Predictability",
        "authors": "Victoria Portnaya",
        "date": "2026-06-28",
        "factors": ["arxiv_magnitude_shrink", "arxiv_lag3_reversal", "arxiv_bounce_proxy"],
        "summary": "Sign/Magnitude分解：区分收益的方向和幅度，发现幅度收缩效应和滞后3日方向反转",
    },
    "2605.12977": {
        "title": "Enhancing a Risk Model by Adding Transient Statistical Factors",
        "authors": "Tzikas, Candès, Hastie, Boyd, Kochenderfer, Kahn",
        "date": "2026-05-13",
        "factors": ["arxiv_residual_ma20"],
        "summary": "瞬态统计因子：从价格序列中提取残差成分，捕捉短期均值回归效应",
    },
    "2605.13407": {
        "title": "Vector-Quantized Discrete Latent Factors (PRISM-VQ)",
        "authors": "Namhyoung Kim, Jae Wook Song",
        "date": "2026-05-13",
        "factors": ["arxiv_regime"],
        "summary": "VQ-inspired regime因子：基于波动率状态的离散隐因子，识别市场状态转换",
    },
}


ARXIV_IMPLEMENTED_DETAILS: dict[str, dict[str, object]] = {
    "arxiv_magnitude_shrink": {
        "paper_id": "2606.29591",
        "formula": "-log(1 + abs(ret_t-1) * 100)",
        "description": "幅度收缩因子：基于Portnaya论文的Sign/Magnitude分解，昨日收益率绝对值越小，今日预期波动越小。",
        "required_fields": ["close"],
        "parameters": {"lag": 1},
        "notes": ["取绝对值后取对数，再取负值。", "论文发现幅度收缩效应具有预测能力。"],
        "original_ic_ir": -0.855,
        "ann_ret": 6.16,
    },
    "arxiv_lag3_reversal": {
        "paper_id": "2606.29591",
        "formula": "-ret_3d.shift(1)",
        "description": "滞后3日反转因子：基于Portnaya论文，方向反转效应在滞后3日最强，而非传统的滞后1日。",
        "required_fields": ["close"],
        "parameters": {"window": 3, "lag": 1},
        "notes": ["与传统反转因子不同，使用滞后3日而非滞后1日。", "论文发现lag-3反转效应更稳定。"],
        "original_ic_ir": -1.920,
        "ann_ret": 6.21,
    },
    "arxiv_bounce_proxy": {
        "paper_id": "2606.29591",
        "formula": "-abs(ret_t-1) * I(abs(ret_t-1) > 2%)",
        "description": "反弹代理因子：当昨日出现大于2%的大幅波动时，预期今日出现均值回归反弹。",
        "required_fields": ["close"],
        "parameters": {"threshold": 0.02, "lag": 1},
        "notes": ["条件因子，仅在大幅波动时生效。", "捕捉买卖价差反弹效应。"],
        "original_ic_ir": -1.065,
        "ann_ret": 6.04,
    },
    "arxiv_residual_ma20": {
        "paper_id": "2605.12977",
        "formula": "-(close - MA20(close)) / close",
        "description": "瞬态统计因子：基于Tzikas et al论文，从20日均线残差中提取的短期均值回归信号。",
        "required_fields": ["close"],
        "parameters": {"window": 20},
        "notes": ["论文使用PCA提取残差因子，这里简化为20日均线残差。", "取负值体现均值回归：价格高于均线时预期下跌。"],
        "original_ic_ir": -10.025,
        "ann_ret": 4.40,
    },
    "arxiv_regime": {
        "paper_id": "2605.13407",
        "formula": "-(vol_20 / vol_60 - 1)",
        "description": "波动率状态因子：基于Kim/Song的PRISM-VQ论文，识别波动率扩张/收缩状态，偏好收缩期。",
        "required_fields": ["close"],
        "parameters": {"short_window": 20, "long_window": 60},
        "notes": ["值为负表示波动率收缩，是多头信号。", "论文使用VQ离散化，这里简化为连续波动率比值。"],
        "original_ic_ir": -2.306,
        "ann_ret": 7.05,
    },
}


def arxiv_specs() -> list[FactorResearchSpec]:
    specs = []
    for factor_name, details in ARXIV_IMPLEMENTED_DETAILS.items():
        specs.append(
            FactorResearchSpec(
                factor_name=factor_name,
                library=ARXIV_SOURCE,
                version=ARXIV_VERSION,
                description=details["description"],
                formula=details["formula"],
                required_fields=details["required_fields"],
                parameters=details.get("parameters", {}),
                tags=["arxiv", "academic", "research"],
                validation_targets=ARXIV_COMMON_THRESHOLDS,
                metadata={
                    "paper_id": details.get("paper_id"),
                    "paper_title": ARXIV_PAPERS.get(details.get("paper_id", ""), {}).get("title"),
                    "authors": ARXIV_PAPERS.get(details.get("paper_id", ""), {}).get("authors"),
                    "original_ic_ir": details.get("original_ic_ir"),
                    "ann_ret": details.get("ann_ret"),
                },
            )
        )
    return specs
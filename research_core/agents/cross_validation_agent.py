"""
交叉验证智能体 - 验证因子有效性并生成验证报告
"""
from __future__ import annotations
from typing import Dict, List, Any
from datetime import datetime


class CrossValidationAgent:
    """交叉验证智能体"""

    def __init__(self):
        self._validation_engine = None
        self._factor_lab = None

    def _init_modules(self):
        if self._validation_engine is None:
            from research_core.validation_engine import (
                ICVerifier,
                ic_bootstrap_test,
            )
            self._validation_engine = {
                "ICVerifier": ICVerifier,
                "ic_bootstrap": ic_bootstrap_test,
            }

        if self._factor_lab is None:
            from research_core.factor_lab_web import (
                build_factor_view,
            )
            from research_core.factor_lab import (
                FactorLabWorkspaceConfig,
            )
            self._factor_lab = {
                "build_factor_view": build_factor_view,
                "WorkspaceConfig": FactorLabWorkspaceConfig,
            }

    async def validate_factor(self, factor_id: str) -> Dict[str, Any]:
        """验证单个因子"""
        self._init_modules()

        config = self._factor_lab["WorkspaceConfig"]()
        factor_view = self._factor_lab["build_factor_view"](factor_id, config)

        ic_values = []
        if "ic_series" in factor_view:
            ic_values = factor_view["ic_series"]
        elif factor_view.get("ic_mean"):
            ic_values = [factor_view["ic_mean"]] * 50

        verifier = self._validation_engine["ICVerifier"]()
        result = verifier.verify(ic_values)

        bootstrap = self._validation_engine["ic_bootstrap"](ic_values)

        return {
            "factor_id": factor_id,
            "name": factor_view.get("name", factor_id),
            "is_significant": result.is_significant,
            "confidence_level": result.confidence_level,
            "p_value": result.p_value,
            "bootstrap_result": bootstrap,
            "evidence_level": self._determine_evidence_level(result, factor_view),
        }

    async def batch_validate(self, factor_ids: List[str]) -> Dict[str, Any]:
        """批量验证因子"""
        results = []
        for factor_id in factor_ids:
            try:
                result = await self.validate_factor(factor_id)
                results.append(result)
            except Exception as e:
                results.append({
                    "factor_id": factor_id,
                    "error": str(e),
                })

        significant_count = sum(1 for r in results if r.get("is_significant"))
        moderate_count = sum(1 for r in results if r.get("evidence_level") == "moderate")

        return {
            "total_factors": len(factor_ids),
            "validated_count": len(results),
            "significant_count": significant_count,
            "moderate_count": moderate_count,
            "insignificant_count": len(results) - significant_count - moderate_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def generate_report(self, factor_ids: List[str]) -> Dict[str, Any]:
        """生成验证报告"""
        validation_results = await self.batch_validate(factor_ids)

        report = {
            "report_type": "cross_validation",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_factors": validation_results["total_factors"],
                "significant_factors": validation_results["significant_count"],
                "moderate_factors": validation_results["moderate_count"],
                "insignificant_factors": validation_results["insignificant_count"],
                "pass_rate": round(
                    validation_results["significant_count"] / validation_results["total_factors"],
                    2
                ) if validation_results["total_factors"] > 0 else 0,
            },
            "recommendations": self._generate_recommendations(validation_results),
            "detailed_results": validation_results["results"],
        }

        return report

    def _determine_evidence_level(self, result, factor_view) -> str:
        """确定证据等级"""
        ic_mean = factor_view.get("ic_mean", 0)
        icir = factor_view.get("icir", 0)

        if result.is_significant and icir > 0.5:
            return "strong"
        elif result.is_significant or icir > 0.3:
            return "moderate"
        else:
            return "weak"

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []

        if results["significant_count"] == 0:
            recommendations.append("未发现显著有效的因子，建议调整因子筛选策略")
        elif results["significant_count"] < results["total_factors"] * 0.3:
            recommendations.append("显著因子占比较低，建议扩大因子搜索范围")
        else:
            recommendations.append("发现较多显著因子，建议进一步优化组合")

        return recommendations
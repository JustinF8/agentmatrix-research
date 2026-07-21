"""
因子研究智能体 - 自动化执行因子发现、评估、回测和验证流程
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime


class FactorResearchAgent:
    """因子研究智能体"""

    def __init__(self):
        self._factor_lab = None
        self._strategy_engine = None
        self._validation_engine = None

    def _init_modules(self):
        if self._factor_lab is None:
            from research_core.factor_lab import (
                FactorLabWorkspaceConfig,
                run_alpha101_research_job,
                get_factor_lab_overview,
                get_factor_lab_job,
                list_factor_lab_jobs,
            )
            from research_core.factor_lab_web import (
                build_factor_library_view,
                build_factor_view,
                build_research_analysis_view,
            )
            self._factor_lab = {
                "WorkspaceConfig": FactorLabWorkspaceConfig,
                "run_alpha101": run_alpha101_research_job,
                "overview": get_factor_lab_overview,
                "get_job": get_factor_lab_job,
                "list_jobs": list_factor_lab_jobs,
                "build_library_view": build_factor_library_view,
                "build_factor_view": build_factor_view,
                "build_research_view": build_research_analysis_view,
            }

        if self._strategy_engine is None:
            from research_core.strategy_engine import (
                run_backtest,
                calculate_performance_metrics,
            )
            self._strategy_engine = {
                "run_backtest": run_backtest,
                "calculate_metrics": calculate_performance_metrics,
            }

        if self._validation_engine is None:
            from research_core.validation_engine import (
                ICVerifier,
                ic_bootstrap_test,
            )
            self._validation_engine = {
                "ICVerifier": ICVerifier,
                "ic_bootstrap": ic_bootstrap_test,
            }

    async def discover_factors(self, source: str = "alpha101",
                              limit: int = 10) -> List[Dict[str, Any]]:
        """发现新因子"""
        self._init_modules()

        config = self._factor_lab["WorkspaceConfig"]()
        overview = self._factor_lab["overview"](config)

        factors = []
        for lib in overview.get("factor_sets", []):
            if source.lower() in lib.get("library", "").lower():
                library_view = self._factor_lab["build_library_view"](config)
                factor_list = list(library_view.get("factors", {}).items())[:limit]
                for factor_id, factor_data in factor_list:
                    factors.append({
                        "factor_id": factor_id,
                        "name": factor_data.get("name", factor_id),
                        "library": lib.get("library"),
                        "status": factor_data.get("status", "unknown"),
                    })

        return factors

    async def evaluate_factor(self, factor_id: str) -> Dict[str, Any]:
        """评估因子"""
        self._init_modules()

        config = self._factor_lab["WorkspaceConfig"]()
        factor_view = self._factor_lab["build_factor_view"](factor_id, config)

        evaluation = {
            "factor_id": factor_id,
            "name": factor_view.get("name", factor_id),
            "ic_mean": factor_view.get("ic_mean"),
            "ic_std": factor_view.get("ic_std"),
            "icir": factor_view.get("icir"),
            "rank_ic_mean": factor_view.get("rank_ic_mean"),
            "good_ic_ratio": factor_view.get("good_ic_ratio"),
        }

        return evaluation

    async def backtest_factor(self, factor_id: str,
                             params: Optional[Dict] = None) -> Dict[str, Any]:
        """回测因子"""
        self._init_modules()

        backtest_params = params or {
            "strategy_name": "因子选股策略",
            "factor_ids": [factor_id],
            "rebalance_freq": "monthly",
            "cost_model": "30bp",
        }

        result = self._strategy_engine["run_backtest"](backtest_params)
        metrics = self._strategy_engine["calculate_metrics"](result)

        return {
            "factor_id": factor_id,
            "backtest_result": result,
            "metrics": metrics,
        }

    async def validate_factor(self, factor_id: str,
                             ic_values: List[float]) -> Dict[str, Any]:
        """验证因子"""
        self._init_modules()

        verifier = self._validation_engine["ICVerifier"]()
        result = verifier.verify(ic_values)

        bootstrap_result = self._validation_engine["ic_bootstrap"](ic_values)

        return {
            "factor_id": factor_id,
            "is_significant": result.is_significant,
            "p_value": result.p_value,
            "confidence_level": result.confidence_level,
            "bootstrap_result": bootstrap_result,
        }

    async def run_research_pipeline(self, factors: List[str],
                                    goal: str = "筛选有效因子") -> Dict[str, Any]:
        """运行完整研究流程"""
        self._init_modules()

        results = []
        for factor_id in factors:
            eval_result = await self.evaluate_factor(factor_id)
            bt_result = await self.backtest_factor(factor_id)

            ic_values = []
            if eval_result.get("ic_mean"):
                ic_values = [eval_result["ic_mean"]] * 20

            validation = await self.validate_factor(factor_id, ic_values)

            results.append({
                "factor_id": factor_id,
                "evaluation": eval_result,
                "backtest": bt_result,
                "validation": validation,
            })

        return {
            "goal": goal,
            "factors": factors,
            "results": results,
            "completed_at": datetime.now().isoformat(),
        }
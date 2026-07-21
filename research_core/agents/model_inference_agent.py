"""
模型推理智能体 - 整合策略引擎和风控能力
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime


class ModelInferenceAgent:
    """模型推理智能体"""

    def __init__(self):
        self._strategy_engine = None
        self._risk_engine = None

    def _init_modules(self):
        if self._strategy_engine is None:
            from research_core.strategy_engine import (
                run_backtest,
                calculate_performance_metrics,
                list_templates,
                get_template,
            )
            self._strategy_engine = {
                "run_backtest": run_backtest,
                "calculate_metrics": calculate_performance_metrics,
                "list_templates": list_templates,
                "get_template": get_template,
            }

        if self._risk_engine is None:
            from research_core.risk_rule_engine import (
                DrawdownTracker,
                DrawdownController,
            )
            self._risk_engine = {
                "DrawdownTracker": DrawdownTracker,
                "DrawdownController": DrawdownController,
            }

    async def predict_factor_effectiveness(self, factor_data: Dict[str, Any]) -> Dict[str, Any]:
        """预测因子有效性"""
        self._init_modules()

        ic_mean = factor_data.get("ic_mean", 0)
        icir = factor_data.get("icir", 0)
        sharpe = factor_data.get("sharpe", 0)

        score = (abs(ic_mean) * 0.4 + icir * 0.3 + sharpe * 0.3)
        effectiveness = "strong" if score > 0.3 else "moderate" if score > 0.1 else "weak"

        return {
            "factor_id": factor_data.get("factor_id"),
            "effectiveness_score": round(score, 4),
            "effectiveness_level": effectiveness,
            "confidence": min(0.95, 0.6 + score * 2),
            "recommendation": self._generate_recommendation(effectiveness),
            "timestamp": datetime.now().isoformat(),
        }

    async def run_strategy_backtest(self, strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """运行策略回测"""
        self._init_modules()
        return self._strategy_engine["run_backtest"](strategy_params)

    async def evaluate_risk(self, nav_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估风险"""
        self._init_modules()

        tracker = self._risk_engine["DrawdownTracker"]()
        for point in nav_data:
            tracker.record(point.get("date", ""), point.get("nav", 0))

        controller = self._risk_engine["DrawdownController"]()
        return {
            "max_drawdown": tracker.max_drawdown,
            "risk_action": controller.check(tracker.max_drawdown).name,
            "recommendations": controller.recommendations,
        }

    def _generate_recommendation(self, effectiveness: str) -> str:
        """生成推荐"""
        if effectiveness == "strong":
            return "因子有效性强，建议纳入策略组合"
        elif effectiveness == "moderate":
            return "因子有效性中等，建议进一步验证"
        else:
            return "因子有效性弱，建议排除或改进"

    async def get_model_list(self) -> List[Dict[str, Any]]:
        """获取模型列表"""
        self._init_modules()
        templates = self._strategy_engine["list_templates"]()
        return [
            {
                "model_id": t.version,
                "name": t.name,
                "description": t.description,
                "factors": t.factors,
            }
            for t in templates.values()
        ]
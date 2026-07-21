"""
指标计算器 - 计算看板所需的各类指标
"""
from typing import Dict, List, Any
import numpy as np
from .kanban_engine import KanbanRow


class MetricCalculator:
    """指标计算器"""
    
    async def calculate_summary(self, rows: List[KanbanRow]) -> Dict[str, Any]:
        """计算看板汇总统计"""
        if not rows:
            return {}
        
        ic_values = [r.ic_mean for r in rows if r.ic_mean is not None]
        sharpe_values = [r.sharpe_q5 for r in rows if r.sharpe_q5 is not None]
        drawdown_values = [abs(r.max_drawdown_q5) for r in rows if r.max_drawdown_q5 is not None]
        crowding_scores = [r.crowding_score for r in rows if r.crowding_score is not None]
        
        summary = {
            "total_factors": len(rows),
            "factors_by_category": self._count_by_category(rows),
            "ic_statistics": self._calculate_ic_statistics(ic_values),
            "risk_statistics": self._calculate_risk_statistics(drawdown_values),
            "performance_statistics": self._calculate_performance_statistics(sharpe_values),
            "risk_control_summary": self._calculate_risk_control_summary(crowding_scores),
            "top_factors": self._get_top_factors(rows, top_n=10),
        }
        
        return summary
    
    def _count_by_category(self, rows: List[KanbanRow]) -> Dict[str, int]:
        """按分类统计"""
        counts = {}
        for row in rows:
            counts[row.category] = counts.get(row.category, 0) + 1
        return counts
    
    def _calculate_ic_statistics(self, ic_values: List[float]) -> Dict[str, Any]:
        """计算IC统计"""
        if not ic_values:
            return {}
        
        ic_arr = np.array(ic_values)
        return {
            "mean_ic": round(np.mean(ic_arr), 4),
            "median_ic": round(np.median(ic_arr), 4),
            "std_ic": round(np.std(ic_arr), 4),
            "positive_ic_ratio": round(sum(1 for ic in ic_arr if ic > 0) / len(ic_arr), 2),
            "ic_ir": round(np.mean(ic_arr) / np.std(ic_arr), 2) if np.std(ic_arr) > 0 else 0,
        }
    
    def _calculate_risk_statistics(self, drawdown_values: List[float]) -> Dict[str, Any]:
        """计算风险统计"""
        if not drawdown_values:
            return {}
        
        dd_arr = np.array(drawdown_values)
        return {
            "mean_drawdown": round(np.mean(dd_arr), 4),
            "max_drawdown": round(np.max(dd_arr), 4),
            "risky_factors": sum(1 for dd in dd_arr if dd >= 0.15),
        }
    
    def _calculate_performance_statistics(self, sharpe_values: List[float]) -> Dict[str, Any]:
        """计算绩效统计"""
        if not sharpe_values:
            return {}
        
        sharpe_arr = np.array(sharpe_values)
        return {
            "mean_sharpe": round(np.mean(sharpe_arr), 2),
            "good_sharpe_factors": sum(1 for s in sharpe_arr if s > 0.5),
        }
    
    def _calculate_risk_control_summary(self, crowding_scores: List[float]) -> Dict[str, Any]:
        """计算风控汇总"""
        if not crowding_scores:
            return {}
        
        return {
            "crowding_mean": round(np.mean(crowding_scores), 4),
            "overcrowded_factors": sum(1 for cs in crowding_scores if cs and cs > 0.7),
        }
    
    def _get_top_factors(self, rows: List[KanbanRow], top_n: int = 10) -> List[Dict[str, Any]]:
        """获取表现最好的因子"""
        sorted_rows = sorted(rows, key=lambda x: abs(x.ic_mean or 0), reverse=True)
        return [r.dict() for r in sorted_rows[:top_n]]
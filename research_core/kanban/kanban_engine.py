"""
看板引擎 - 驱动因子看板的核心逻辑
"""
from typing import Dict, List, Any, Optional
import numpy as np


class KanbanRow:
    """看板行数据"""
    
    def __init__(self, factor_id: str, **kwargs):
        self.factor_id = factor_id
        self.factor_name = kwargs.get("factor_name", factor_id)
        self.category = kwargs.get("category", "unknown")
        self.ic_mean = kwargs.get("ic_mean")
        self.rank_ic_mean = kwargs.get("rank_ic_mean")
        self.icir = kwargs.get("icir")
        self.ir = kwargs.get("ir")
        self.good_ic_ratio = kwargs.get("good_ic_ratio")
        self.crowding_score = kwargs.get("crowding_score")
        self.max_drawdown_q5 = kwargs.get("max_drawdown_q5")
        self.sharpe_q5 = kwargs.get("sharpe_q5")
    
    def dict(self):
        """转为字典"""
        return {
            "factor_id": self.factor_id,
            "factor_name": self.factor_name,
            "category": self.category,
            "ic_mean": self.ic_mean,
            "rank_ic_mean": self.rank_ic_mean,
            "icir": self.icir,
            "ir": self.ir,
            "good_ic_ratio": self.good_ic_ratio,
            "crowding_score": self.crowding_score,
            "max_drawdown_q5": self.max_drawdown_q5,
            "sharpe_q5": self.sharpe_q5,
        }


class KanbanEngine:
    """看板引擎"""
    
    def __init__(self):
        self._factor_lab = None
    
    def _init_modules(self):
        if self._factor_lab is None:
            from research_core.factor_lab_web import (
                build_factor_library_view,
                build_factor_view,
            )
            from research_core.factor_lab import (
                FactorLabWorkspaceConfig,
            )
            self._factor_lab = {
                "build_library_view": build_factor_library_view,
                "build_factor_view": build_factor_view,
                "WorkspaceConfig": FactorLabWorkspaceConfig,
            }
    
    async def initialize(self):
        """初始化"""
        self._init_modules()
    
    async def generate_rows(self, factor_data: List[Dict], **kwargs) -> List[KanbanRow]:
        """生成看板行"""
        rows = []
        for data in factor_data:
            row = KanbanRow(
                factor_id=data.get("factor_id", data.get("id", "")),
                factor_name=data.get("factor_name", data.get("name", "")),
                category=data.get("category", "unknown"),
                ic_mean=data.get("ic_mean"),
                rank_ic_mean=data.get("rank_ic_mean"),
                icir=data.get("icir"),
                ir=data.get("ir"),
                good_ic_ratio=data.get("good_ic_ratio"),
                crowding_score=data.get("crowding_score"),
                max_drawdown_q5=data.get("max_drawdown_q5"),
                sharpe_q5=data.get("sharpe_q5"),
            )
            rows.append(row)
        return rows
    
    async def get_factor_detail(self, factor_id: str) -> Optional[Dict]:
        """获取因子详情"""
        self._init_modules()
        config = self._factor_lab["WorkspaceConfig"]()
        return self._factor_lab["build_factor_view"](factor_id, config)
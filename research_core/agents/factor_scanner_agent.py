"""
因子扫描智能体 - 批量扫描因子库并生成统计报告
"""
from __future__ import annotations
from typing import Dict, List, Any


class FactorLibraryScanner:
    """因子库扫描器"""

    def __init__(self):
        self._factor_lab = None

    def _init_modules(self):
        if self._factor_lab is None:
            from research_core.factor_lab import (
                FactorLabWorkspaceConfig,
                get_factor_lab_overview,
            )
            from research_core.factor_lab_web import (
                build_factor_library_view,
            )
            self._factor_lab = {
                "WorkspaceConfig": FactorLabWorkspaceConfig,
                "overview": get_factor_lab_overview,
                "build_library_view": build_factor_library_view,
            }

    async def scan_all_libraries(self) -> Dict[str, Any]:
        """扫描所有因子库"""
        self._init_modules()

        config = self._factor_lab["WorkspaceConfig"]()
        overview = self._factor_lab["overview"](config)

        libraries = []
        for lib in overview.get("factor_sets", []):
            library_view = self._factor_lab["build_library_view"](config)
            factors = library_view.get("factors", {})

            stats = await self._calculate_library_stats(factors)
            libraries.append({
                "name": lib.get("library"),
                "catalog_name": lib.get("catalog_name"),
                "total_factors": len(factors),
                "status": lib.get("status"),
                "stats": stats,
            })

        return {"libraries": libraries, "total_libraries": len(libraries)}

    async def _calculate_library_stats(self, factors: Dict[str, Any]) -> Dict[str, Any]:
        """计算因子库统计"""
        ic_values = []
        rank_ic_values = []
        icir_values = []

        for factor_id, data in factors.items():
            if data.get("ic_mean"):
                ic_values.append(data["ic_mean"])
            if data.get("rank_ic_mean"):
                rank_ic_values.append(data["rank_ic_mean"])
            if data.get("icir"):
                icir_values.append(data["icir"])

        import numpy as np
        return {
            "mean_ic": round(np.mean(ic_values), 4) if ic_values else None,
            "mean_rank_ic": round(np.mean(rank_ic_values), 4) if rank_ic_values else None,
            "mean_icir": round(np.mean(icir_values), 2) if icir_values else None,
            "positive_ic_count": sum(1 for ic in ic_values if ic > 0),
            "negative_ic_count": sum(1 for ic in ic_values if ic < 0),
            "total_evaluated": len(ic_values),
        }


class FactorScannerAgent:
    """因子扫描智能体"""

    def __init__(self):
        self.scanner = FactorLibraryScanner()

    async def run_scan(self) -> Dict[str, Any]:
        """执行扫描任务"""
        result = await self.scanner.scan_all_libraries()

        summary = {
            "total_libraries": result["total_libraries"],
            "total_factors": sum(lib["total_factors"] for lib in result["libraries"]),
            "avg_ic": self._calculate_global_avg(result["libraries"]),
            "libraries": result["libraries"],
        }

        return summary

    def _calculate_global_avg(self, libraries: List[Dict]) -> float:
        """计算全局平均IC"""
        total_ic = 0
        count = 0
        for lib in libraries:
            if lib["stats"]["mean_ic"]:
                total_ic += lib["stats"]["mean_ic"] * lib["total_factors"]
                count += lib["total_factors"]
        return round(total_ic / count, 4) if count > 0 else 0
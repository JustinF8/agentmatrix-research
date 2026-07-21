"""
research_core - 因子研究核心模块
整合三个方案的优化能力：智能体、服务注册、看板分析
"""
from .agents import (
    FactorResearchAgent,
    FactorScannerAgent,
    FactorLibraryScanner,
    CrossValidationAgent,
    ModelInferenceAgent,
)
from .registry import (
    ServiceRegistry,
    ServiceInfo,
    TaskOrchestrator,
)
from .kanban import (
    KanbanEngine,
    MetricCalculator,
)

__all__ = [
    "FactorResearchAgent",
    "FactorScannerAgent",
    "FactorLibraryScanner",
    "CrossValidationAgent",
    "ModelInferenceAgent",
    "ServiceRegistry",
    "ServiceInfo",
    "TaskOrchestrator",
    "KanbanEngine",
    "MetricCalculator",
]
# adapters 包：把外部项目（如 model-main Fusion Hub）接入因子看板后端的适配器。
from .model_adapter import ModelAdapter, register_model_routes

__all__ = ["ModelAdapter", "register_model_routes"]

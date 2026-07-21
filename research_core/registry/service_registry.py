"""
服务注册中心 - 管理所有服务的注册与发现
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel


class ServiceInfo(BaseModel):
    """服务信息模型"""
    service_id: str
    service_name: str
    service_type: str
    version: str = "1.0.0"
    endpoint: str
    metadata: Dict[str, Any] = {}
    status: str = "active"
    last_heartbeat: datetime = datetime.now()
    registered_at: datetime = datetime.now()
    capabilities: List[str] = []


class ServiceRegistry:
    """服务注册中心"""
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.heartbeat_timeout = timedelta(seconds=60)
        
    async def initialize(self):
        """初始化"""
        pass
        
    async def register(self, service_info: ServiceInfo) -> bool:
        """注册服务"""
        self.services[service_info.service_id] = service_info
        return True
    
    async def deregister(self, service_id: str) -> bool:
        """注销服务"""
        if service_id in self.services:
            del self.services[service_id]
            return True
        return False
    
    async def discover(self, service_type: str = None) -> List[ServiceInfo]:
        """发现服务"""
        if service_type:
            return [s for s in self.services.values() if s.service_type == service_type]
        return list(self.services.values())
    
    async def heartbeat(self, service_id: str) -> bool:
        """心跳检测"""
        if service_id in self.services:
            self.services[service_id].last_heartbeat = datetime.now()
            return True
        return False
    
    async def get_all_services(self) -> List[Dict]:
        """获取所有服务状态"""
        return [
            {
                "id": sid,
                "name": info.service_name,
                "type": info.service_type,
                "status": info.status,
                "endpoint": info.endpoint,
                "last_heartbeat": info.last_heartbeat.isoformat()
            }
            for sid, info in self.services.items()
        ]
    
    async def close(self):
        """关闭"""
        pass
"""
任务编排器 - 编排和调度研究任务
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchTask:
    """研究任务"""
    
    def __init__(self, task_id: str, goal: str, **kwargs):
        self.task_id = task_id
        self.goal = goal
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.result = None
        self.kwargs = kwargs


class TaskOrchestrator:
    """任务编排器"""
    
    def __init__(self, registry=None):
        self.registry = registry
        self.tasks: Dict[str, ResearchTask] = {}
        
    async def submit_task(self, goal: str, **kwargs) -> ResearchTask:
        """提交任务"""
        task_id = f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task = ResearchTask(task_id, goal, **kwargs)
        self.tasks[task_id] = task
        return task
    
    async def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    async def update_task(self, task_id: str, status: TaskStatus, result=None):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].result = result
            self.tasks[task_id].updated_at = datetime.now()
    
    async def get_active_task_count(self) -> int:
        """获取活跃任务数"""
        return sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
    
    async def list_tasks(self, status: TaskStatus = None) -> List[ResearchTask]:
        """列出任务"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
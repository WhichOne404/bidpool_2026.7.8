"""
监控智能体 - 负责任务状态监控和告警
"""
from typing import Dict, Any, Optional
from agents.base import BaseAgent, AgentResult
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MonitorAgent(BaseAgent):
    """监控智能体"""

    name = "monitor_agent"
    description = "负责任务状态监控、异常告警和日志收集"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.task_status: Dict[str, Dict] = {}

    def execute(self, task_data: Dict[str, Any]) -> AgentResult:
        """
        执行监控任务

        Args:
            task_data: {
                "action": "get_status" | "get_logs" | "health_check",
                "task_id": "optional task id"
            }
        """
        action = task_data.get("action", "get_status")

        if action == "get_status":
            return self._get_status(task_data.get("task_id"))
        elif action == "get_logs":
            return self._get_logs(task_data.get("task_id"))
        elif action == "health_check":
            return self._health_check()
        else:
            return AgentResult(
                success=False,
                message=f"未知操作: {action}",
                error="Unknown action"
            )

    def _get_status(self, task_id: Optional[str] = None) -> AgentResult:
        """获取任务状态"""
        if task_id:
            status = self.task_status.get(task_id, {})
            return AgentResult(
                success=True,
                message=f"任务 {task_id} 状态",
                data={"task_id": task_id, "status": status}
            )
        else:
            return AgentResult(
                success=True,
                message="所有任务状态",
                data={"tasks": self.task_status}
            )

    def _get_logs(self, task_id: Optional[str] = None) -> AgentResult:
        """获取日志"""
        # 这里可以从文件或数据库读取日志
        return AgentResult(
            success=True,
            message="日志查询",
            data={"logs": []}
        )

    def _health_check(self) -> AgentResult:
        """健康检查"""
        return AgentResult(
            success=True,
            message="系统健康",
            data={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "agents": {
                    "crawler": "ready",
                    "filter": "ready",
                    "dispatch": "ready",
                    "orchestrator": "ready"
                }
            }
        )

    def update_task_status(self, task_id: str, status: Dict):
        """更新任务状态"""
        self.task_status[task_id] = {
            **status,
            "updated_at": datetime.now().isoformat()
        }
"""
Agent 基类定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import uuid
import time


@dataclass
class AgentResult:
    """Agent执行结果"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """Agent基类"""

    name: str = "base_agent"
    description: str = "Base Agent"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agent_id = str(uuid.uuid4())

    @abstractmethod
    def execute(self, task_data: Dict[str, Any]) -> AgentResult:
        """
        执行Agent任务

        Args:
            task_data: 任务数据

        Returns:
            AgentResult: 执行结果
        """
        pass

    def validate_input(self, task_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        return True

    def pre_process(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """预处理"""
        return task_data

    def post_process(self, result: AgentResult) -> AgentResult:
        """后处理"""
        return result

    def run(self, task_data: Dict[str, Any]) -> AgentResult:
        """
        运行Agent（包含完整的执行流程）
        """
        if not self.validate_input(task_data):
            return AgentResult(
                success=False,
                message="输入数据验证失败",
                error="Invalid input data"
            )

        processed_data = self.pre_process(task_data)
        result = self.execute(processed_data)
        return self.post_process(result)
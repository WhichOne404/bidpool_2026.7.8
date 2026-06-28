"""
对话记忆管理器 - 支持多轮对话上下文
"""
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """对话状态"""
    # 对话历史
    history: List[Dict[str, str]] = field(default_factory=list)
    # 当前操作阶段: idle / waiting_group / waiting_bids / waiting_confirm
    stage: str = "idle"
    # 待处理数据
    pending_data: Dict[str, Any] = field(default_factory=dict)
    # 最后活动时间
    last_active: float = field(default_factory=time.time)
    # 会话ID
    session_id: str = ""


class ConversationMemory:
    """对话记忆管理器"""

    def __init__(self, max_history: int = 20, expire_time: int = 3600):
        """
        Args:
            max_history: 最大历史消息数
            expire_time: 会话过期时间（秒）
        """
        self.max_history = max_history
        self.expire_time = expire_time
        self._conversations: Dict[str, ConversationState] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> ConversationState:
        """获取或创建对话状态"""
        with self._lock:
            # 清理过期会话
            self._cleanup_expired()

            if session_id not in self._conversations:
                self._conversations[session_id] = ConversationState(
                    session_id=session_id
                )
                logger.info(f"创建新会话: {session_id}")

            conv = self._conversations[session_id]
            conv.last_active = time.time()
            return conv

    def add_message(self, session_id: str, role: str, content: str):
        """添加消息到历史"""
        conv = self.get_or_create(session_id)
        conv.history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })

        # 限制历史长度
        if len(conv.history) > self.max_history:
            conv.history = conv.history[-self.max_history:]

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取对话历史（不含timestamp）"""
        conv = self.get_or_create(session_id)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conv.history
        ]

    def set_stage(self, session_id: str, stage: str, pending_data: Dict = None):
        """设置当前操作阶段"""
        conv = self.get_or_create(session_id)
        conv.stage = stage
        if pending_data:
            conv.pending_data = pending_data
        logger.info(f"会话 {session_id} 进入阶段: {stage}")

    def get_stage(self, session_id: str) -> str:
        """获取当前阶段"""
        conv = self.get_or_create(session_id)
        return conv.stage

    def get_pending_data(self, session_id: str) -> Dict:
        """获取待处理数据"""
        conv = self.get_or_create(session_id)
        return conv.pending_data

    def update_pending_data(self, session_id: str, data: Dict):
        """更新待处理数据"""
        conv = self.get_or_create(session_id)
        conv.pending_data.update(data)

    def clear_state(self, session_id: str):
        """清除操作状态（回到 idle）"""
        conv = self.get_or_create(session_id)
        conv.stage = "idle"
        conv.pending_data = {}

    def reset(self, session_id: str):
        """重置整个会话"""
        with self._lock:
            if session_id in self._conversations:
                del self._conversations[session_id]
                logger.info(f"重置会话: {session_id}")

    def _cleanup_expired(self):
        """清理过期会话"""
        current_time = time.time()
        expired = [
            sid for sid, conv in self._conversations.items()
            if current_time - conv.last_active > self.expire_time
        ]
        for sid in expired:
            del self._conversations[sid]
            logger.info(f"清理过期会话: {sid}")


# 全局对话记忆实例
global _memory_instance
_memory_instance = None


def get_memory() -> ConversationMemory:
    """获取全局对话记忆实例"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ConversationMemory()
    return _memory_instance
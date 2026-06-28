"""
Chat API 路由 - 支持多轮对话记忆
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict
from agents.orchestrator_agent import OrchestratorAgent
from llm.prompts import CHAT_WELCOME
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化编排Agent
orchestrator_agent = OrchestratorAgent()


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    context: Optional[Dict] = None
    session_id: Optional[str] = None  # 会话ID，用于多轮对话


class ChatResponse(BaseModel):
    """对话响应"""
    code: int
    message: str
    data: Optional[Dict] = None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理对话请求 - 支持多轮记忆"""
    try:
        # 获取或生成 session_id
        session_id = request.session_id or "default"

        # 通过编排Agent处理对话
        response = orchestrator_agent.process_chat(
            message=request.message,
            session_id=session_id,
            context=request.context
        )

        return ChatResponse(
            code=0,
            message="success",
            data={
                "response": response,
                "session_id": session_id
            }
        )

    except Exception as e:
        logger.error(f"对话处理失败: {e}")
        return ChatResponse(
            code=-1,
            message=f"处理失败: {str(e)}"
        )


@router.get("/welcome")
async def get_welcome():
    """获取欢迎消息"""
    return {
        "code": 0,
        "data": {"message": CHAT_WELCOME}
    }
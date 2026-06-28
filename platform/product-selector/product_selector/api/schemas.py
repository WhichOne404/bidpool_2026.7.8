"""API 请求和响应数据模式"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    input_type: str = Field(default="dialogue", description="dialogue 或 form")
    input: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    session_id: Optional[str] = Field(None, description="会话ID（多轮对话用）")


class ProductItem(BaseModel):
    id: str
    name: str
    category: str
    description: str
    software_version_count: int
    hardware_version_count: int


class ProductListResponse(BaseModel):
    products: List[ProductItem]


class RecommendResponse(BaseModel):
    status: str = "success"
    type: str  # "recommendation" 或 "question"
    data: Optional[Dict[str, Any]] = None
    question: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    product_count: int
    version: str
    llm_available: bool = False
    vector_search_available: bool = False
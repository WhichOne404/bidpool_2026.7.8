"""配置管理"""
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


def _load_dotenv() -> None:
    """尝试加载 .env 文件，python-dotenv 不可用时忽略"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


@dataclass
class SelectorConfig:
    """选型助手配置"""
    data_dir: str = "data"
    default_discount_min: Decimal = Decimal("0.85")
    default_discount_max: Decimal = Decimal("0.95")
    llm_api_base: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4o"
    embedding_api_base: Optional[str] = None
    embedding_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    enable_vector_search: bool = False  # 向量检索默认关闭，需显式开启
    cache_ttl_seconds: int = 300

    @classmethod
    def from_env(cls, data_dir: str = "data", env_prefix: str = "PS_") -> "SelectorConfig":
        """从环境变量加载配置

        读取的环境变量:
          {prefix}LLM_API_BASE, {prefix}LLM_API_KEY, {prefix}LLM_MODEL
          {prefix}EMBEDDING_API_BASE, {prefix}EMBEDDING_API_KEY, {prefix}EMBEDDING_MODEL
          {prefix}ENABLE_VECTOR_SEARCH
          {prefix}CACHE_TTL_SECONDS
        """
        _load_dotenv()

        def _env(key: str, default=None):
            val = os.environ.get(f"{env_prefix}{key}")
            return val if val else default

        return cls(
            data_dir=data_dir,
            llm_api_base=_env("LLM_API_BASE"),
            llm_api_key=_env("LLM_API_KEY"),
            llm_model=_env("LLM_MODEL", "gpt-4o"),
            embedding_api_base=_env("EMBEDDING_API_BASE"),
            embedding_api_key=_env("EMBEDDING_API_KEY"),
            embedding_model=_env("EMBEDDING_MODEL", "text-embedding-3-small"),
            enable_vector_search=_env("ENABLE_VECTOR_SEARCH", "").lower() == "true",
            cache_ttl_seconds=int(_env("CACHE_TTL_SECONDS", "300")),
        )
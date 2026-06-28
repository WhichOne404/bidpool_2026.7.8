"""LLM Client - OpenAI 兼容接口的轻量封装

同时支持 chat 和 embedding 调用。SDK 不可用或 API 失败时静默降级。
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMClientConfig:
    """LLM API 配置"""
    api_base: str = ""
    api_key: str = ""
    model: str = "gpt-4o"
    timeout: float = 30.0
    max_retries: int = 2


class LLMClient:
    """OpenAI 兼容的 LLM 客户端，支持 chat 和 embedding"""

    def __init__(self, config: LLMClientConfig):
        self._config = config
        self._client = None
        self._available = False
        if not config.api_base or not config.api_key:
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=config.api_base.rstrip("/"),
                api_key=config.api_key,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            self._available = True
        except ImportError:
            pass
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def chat(self, messages: list[dict], **kwargs) -> Optional[str]:
        """发送 chat 请求，返回 response content 或 None"""
        if not self._available:
            return None
        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception:
            return None

    def embed(self, texts: list[str]) -> Optional[list[list[float]]]:
        """生成 embeddings，返回向量列表或 None"""
        if not self._available:
            return None
        try:
            response = self._client.embeddings.create(
                model=self._config.model,
                input=texts,
            )
            return [d.embedding for d in response.data]
        except Exception:
            return None

"""
LLM客户端 - 支持OpenAI接口格式
从 Go 后端配置文件读取配置，实现配置统一
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端 - OpenAI接口格式"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.api_base = self.config.get("api_base", "https://aiapi.chaitin.net/v1")
        self.api_key = self.config.get("api_key", "")
        self.model = self.config.get("model", "gpt-4o")
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.7)

        if not self.api_key:
            logger.warning("未配置API Key")

    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """加载配置文件 - 优先读取Go后端的配置文件"""
        # 优先读取Go后端的配置文件（统一配置）
        # 路径: bidpool-python/../bidpool-go/config/app_config.json
        python_root = Path(__file__).parent.parent  # bidpool-python
        go_config_path = python_root.parent / "bidpool-go" / "config" / "app_config.json"

        if go_config_path.exists():
            try:
                with open(go_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"加载Go后端配置文件: {go_config_path}")
                    llm_config = data.get("llm", {})
                    logger.info(f"LLM配置: model={llm_config.get('model')}, api_base={llm_config.get('api_base')}")
                    return llm_config
            except Exception as e:
                logger.error(f"加载Go配置失败: {e}")

        # 回退到Python本地配置
        if config_path is None:
            config_path = python_root / "config" / "llm_config.json"

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"加载配置文件: {config_path}")
                    return data.get("llm", {})
            except Exception as e:
                logger.error(f"加载配置失败: {e}")

        return {}

    def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """
        发送对话消息

        Args:
            message: 用户消息
            system_prompt: 系统提示词

        Returns:
            回复内容
        """
        if not self.api_key:
            return "错误：未配置API Key"

        try:
            import requests

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": message})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            response = requests.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"API调用失败: {response.status_code} - {response.text}")
                return f"API调用失败: {response.status_code}"

        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return f"API调用异常: {str(e)}"

    def chat_with_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        带历史记录的对话

        Args:
            messages: 消息历史 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 系统提示词

        Returns:
            回复内容
        """
        if not self.api_key:
            return "错误：未配置API Key"

        try:
            import requests

            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            payload = {
                "model": self.model,
                "messages": full_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            response = requests.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"API调用失败: {response.status_code}"

        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return f"API调用异常: {str(e)}"

    def analyze_intent(self, message: str) -> Dict[str, Any]:
        """
        分析用户意图

        Args:
            message: 用户消息

        Returns:
            意图分析结果
        """
        prompt = f"""分析以下用户消息的意图，返回JSON格式结果：

消息: {message}

请分析用户想要做什么操作，返回格式如下：
{{
    "intent": "collect|send|query|unknown",
    "params": {{
        "time_range": "本周|本月|最近7天|...",
        "regions": ["重庆", "四川"],
        "industries": ["金融", "能源"]
    }},
    "confidence": 0.0-1.0
}}

只返回JSON，不要其他内容。"""

        try:
            response = self.chat(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {"intent": "unknown", "params": {}, "confidence": 0.0}

    def classify_bid(self, bid_info: Dict, categories: List[str]) -> str:
        """
        智能分类标讯

        Args:
            bid_info: 标讯信息
            categories: 分类列表

        Returns:
            分类结果
        """
        prompt = f"""请将以下标讯分类到最合适的类别中。

标讯信息：
- 标题: {bid_info.get('title', '')}
- 招标单位: {bid_info.get('tender_unit', '')}
- 行业: {bid_info.get('crm_industry', '')}

可选类别: {', '.join(categories)}

只返回最合适的类别名称，不要其他内容。"""

        return self.chat(prompt)


# 为了兼容旧代码，保留ClaudeClient别名
ClaudeClient = LLMClient
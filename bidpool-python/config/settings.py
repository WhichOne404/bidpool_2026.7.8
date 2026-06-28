"""
配置管理
"""
import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from pathlib import Path


class DingTalkGroupConfig(BaseModel):
    """钉钉群配置"""
    name: str
    webhook_url: str
    industries: List[str] = []


class PlatformCredentials(BaseModel):
    """平台凭证"""
    username: str = ""
    password: str = ""


class LLMConfig(BaseModel):
    """LLM配置"""
    api_base: str = "https://aiapi.chaitin.net/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7


class Settings(BaseModel):
    """系统配置"""
    # LLM配置
    llm: LLMConfig = LLMConfig()

    # 服务配置
    go_backend_url: str = "http://localhost:8080"
    python_service_port: int = 8000

    # 平台凭证
    platforms: Dict[str, PlatformCredentials] = {}

    # 钉钉群配置
    dingtalk_groups: List[DingTalkGroupConfig] = []

    # 默认爬取配置
    default_region_codes: List[str] = ["500000"]  # 重庆
    default_business_type: str = "229"  # 招标数据

    @classmethod
    def load_from_file(cls, path: str = None) -> "Settings":
        """从文件加载配置"""
        if path is None:
            # 支持从环境变量读取配置路径
            env_path = os.getenv("CONFIG_PATH")
            if env_path:
                path = env_path
            else:
                # 默认路径：优先使用 /app/config，然后是本地 config 目录
                docker_path = "/app/config/llm_config.json"
                local_path = Path(__file__).parent / "llm_config.json"
                if os.path.exists(docker_path):
                    path = docker_path
                else:
                    path = local_path

        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                settings = cls()

                # LLM配置
                if "llm" in data:
                    settings.llm = LLMConfig(**data["llm"])

                # 平台配置
                if "platforms" in data:
                    settings.platforms = {
                        k: PlatformCredentials(**v)
                        for k, v in data["platforms"].items()
                    }

                # 钉钉群配置
                if "dingtalk_groups" in data:
                    settings.dingtalk_groups = [
                        DingTalkGroupConfig(**g)
                        for g in data["dingtalk_groups"]
                    ]

                # 服务端口配置
                if "python_service_port" in data:
                    settings.python_service_port = data["python_service_port"]

                # Go 后端 URL
                if "go_backend_url" in data:
                    settings.go_backend_url = data["go_backend_url"]

                # 环境变量覆盖
                if os.getenv("GO_BACKEND_URL"):
                    settings.go_backend_url = os.getenv("GO_BACKEND_URL")

                return settings
            except Exception as e:
                print(f"加载配置失败: {e}")

        return cls()

    def save_to_file(self, path: str = None):
        """保存配置到文件"""
        if path is None:
            path = Path(__file__).parent / "llm_config.json"

        data = {
            "llm": self.llm.model_dump(),
            "platforms": {k: v.model_dump() for k, v in self.platforms.items()},
            "dingtalk_groups": [g.model_dump() for g in self.dingtalk_groups]
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例"""
    global _settings
    if _settings is None:
        _settings = Settings.load_from_file()
    return _settings


def reload_settings():
    """重新加载配置"""
    global _settings
    _settings = Settings.load_from_file()
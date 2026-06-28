"""
爬虫智能体 - 负责标讯数据采集
"""
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentResult
from crawlers.qianlima import QianliMaCrawler
from crawlers.registry import CrawlerRegistry
from config import get_settings
import logging

logger = logging.getLogger(__name__)


class CrawlerAgent(BaseAgent):
    """爬虫智能体"""

    name = "crawler_agent"
    description = "负责标讯数据采集，支持多平台爬取"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.registry = CrawlerRegistry()
        self._init_crawlers()

    def _init_crawlers(self):
        """初始化爬虫"""
        # 注册千里马爬虫
        self.registry.register("qianlima", QianliMaCrawler)

    def _get_credentials(self, platform: str, provided_credentials: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """获取平台凭证"""
        # 如果提供了凭证，直接使用
        if provided_credentials and provided_credentials.get("username") and provided_credentials.get("password"):
            return provided_credentials

        # 否则从配置文件读取
        settings = get_settings()
        if platform in settings.platforms:
            platform_config = settings.platforms[platform]
            return {
                "username": platform_config.username,
                "password": platform_config.password
            }

        return {}

    def execute(self, task_data: Dict[str, Any]) -> AgentResult:
        """
        执行爬取任务

        Args:
            task_data: {
                "platform": "qianlima",
                "region_codes": ["500000", "510000"],
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "credentials": {"username": "...", "password": "..."}
            }
        """
        platform = task_data.get("platform", "qianlima")

        # 获取爬虫实例
        crawler = self.registry.get_crawler(platform)
        if not crawler:
            return AgentResult(
                success=False,
                message=f"未找到平台: {platform}",
                error="Platform not found"
            )

        try:
            # 登录 - 从配置文件获取凭证
            credentials = self._get_credentials(platform, task_data.get("credentials"))
            if not crawler.login(credentials):
                return AgentResult(
                    success=False,
                    message="登录失败",
                    error="Login failed"
                )

            # 搜索
            bids = crawler.search({
                "region_codes": task_data.get("region_codes", []),
                "start_date": task_data.get("start_date"),
                "end_date": task_data.get("end_date")
            })

            logger.info(f"爬取完成，共 {len(bids)} 条标讯")

            return AgentResult(
                success=True,
                message=f"成功爬取 {len(bids)} 条标讯",
                data={"bids": bids, "count": len(bids)}
            )

        except Exception as e:
            logger.error(f"爬取失败: {e}")
            return AgentResult(
                success=False,
                message="爬取失败",
                error=str(e)
            )

    def get_available_platforms(self) -> List[str]:
        """获取可用的平台列表"""
        return self.registry.list_platforms()
"""
爬虫注册表 - 支持动态添加新平台
"""
from typing import Dict, Type, List, Optional
from crawlers.base_crawler import BaseCrawler
import logging

logger = logging.getLogger(__name__)


class CrawlerRegistry:
    """爬虫注册表"""

    _crawlers: Dict[str, Type[BaseCrawler]] = {}

    @classmethod
    def register(cls, platform: str, crawler_class: Type[BaseCrawler]):
        """
        注册爬虫

        Args:
            platform: 平台名称
            crawler_class: 爬虫类
        """
        cls._crawlers[platform] = crawler_class
        logger.info(f"注册爬虫: {platform}")

    @classmethod
    def unregister(cls, platform: str):
        """注销爬虫"""
        if platform in cls._crawlers:
            del cls._crawlers[platform]
            logger.info(f"注销爬虫: {platform}")

    @classmethod
    def get_crawler(cls, platform: str) -> Optional[BaseCrawler]:
        """
        获取爬虫实例

        Args:
            platform: 平台名称

        Returns:
            爬虫实例
        """
        crawler_class = cls._crawlers.get(platform)
        if crawler_class:
            return crawler_class()
        return None

    @classmethod
    def list_platforms(cls) -> List[str]:
        """获取所有已注册的平台"""
        return list(cls._crawlers.keys())

    @classmethod
    def get_info(cls, platform: str) -> Optional[Dict]:
        """获取平台信息"""
        crawler_class = cls._crawlers.get(platform)
        if crawler_class:
            return {
                "name": crawler_class.name,
                "description": crawler_class.description
            }
        return None
"""
爬虫基类定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import requests


@dataclass
class SearchParams:
    """搜索参数"""
    region_codes: List[str]
    start_date: str
    end_date: str
    business_type: str = "229"  # 默认招标数据
    page: int = 1
    limit: int = 100


@dataclass
class BidInfo:
    """标讯信息"""
    id: str
    title: str
    tender_unit: str
    crm_industry: str
    budget: str
    region: str
    publish_date: str
    deadline: str
    open_date: str
    source: str
    link: str
    raw_data: Optional[Dict] = None


class BaseCrawler(ABC):
    """爬虫基类"""

    name: str = "base_crawler"
    description: str = "Base Crawler"

    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False

    @abstractmethod
    def login(self, credentials: Dict[str, str]) -> bool:
        """
        登录平台

        Args:
            credentials: {"username": "...", "password": "..."}

        Returns:
            是否登录成功
        """
        pass

    @abstractmethod
    def search(self, params: SearchParams) -> List[BidInfo]:
        """
        搜索标讯

        Args:
            params: 搜索参数

        Returns:
            标讯列表
        """
        pass

    @abstractmethod
    def get_detail(self, bid_id: str) -> Optional[BidInfo]:
        """
        获取标讯详情

        Args:
            bid_id: 标讯ID

        Returns:
            标讯详情
        """
        pass

    def logout(self):
        """登出"""
        self.session.close()
        self.logged_in = False

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.logged_in
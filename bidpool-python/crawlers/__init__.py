"""
爬虫模块
"""
from .base_crawler import BaseCrawler
from .qianlima import QianliMaCrawler
from .registry import CrawlerRegistry

__all__ = ["BaseCrawler", "QianliMaCrawler", "CrawlerRegistry"]
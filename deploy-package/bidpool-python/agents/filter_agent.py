"""
过滤智能体 - 负责数据清洗和筛选
"""
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentResult
from llm.claude_client import ClaudeClient
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class FilterAgent(BaseAgent):
    """过滤智能体"""

    name = "filter_agent"
    description = "负责标讯数据清洗、去重、筛选和智能分类"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.llm_client = ClaudeClient() if config and config.get("use_llm") else None

    def execute(self, task_data: Dict[str, Any]) -> AgentResult:
        """
        执行过滤任务

        Args:
            task_data: {
                "bids": [...],
                "filters": {
                    "industries": ["金融", "能源"],
                    "keywords": ["招标", "采购"],
                    "exclude_keywords": ["废标"],
                    "min_budget": 100000,
                    "regions": ["重庆", "四川"]
                },
                "use_llm": True
            }
        """
        bids = task_data.get("bids", [])
        filters = task_data.get("filters", {})

        if not bids:
            return AgentResult(
                success=True,
                message="无数据需要过滤",
                data={"bids": [], "count": 0}
            )

        try:
            # 1. 去重
            bids = self._deduplicate(bids)
            logger.info(f"去重后: {len(bids)} 条")

            # 2. 基础过滤
            bids = self._basic_filter(bids, filters)
            logger.info(f"基础过滤后: {len(bids)} 条")

            # 3. LLM智能分类（可选）
            if self.llm_client and filters.get("use_llm"):
                bids = self._llm_classify(bids, filters)
                logger.info(f"LLM分类后: {len(bids)} 条")

            return AgentResult(
                success=True,
                message=f"过滤完成，共 {len(bids)} 条标讯",
                data={"bids": bids, "count": len(bids)}
            )

        except Exception as e:
            logger.error(f"过滤失败: {e}")
            return AgentResult(
                success=False,
                message="过滤失败",
                error=str(e)
            )

    def _deduplicate(self, bids: List[Dict]) -> List[Dict]:
        """去重（基于标题哈希）"""
        seen = set()
        unique_bids = []

        for bid in bids:
            title = bid.get("title", "")
            if not title:
                continue

            # 生成标题哈希
            title_hash = hashlib.md5(title.encode()).hexdigest()

            if title_hash not in seen:
                seen.add(title_hash)
                unique_bids.append(bid)

        return unique_bids

    def _basic_filter(self, bids: List[Dict], filters: Dict) -> List[Dict]:
        """基础过滤"""
        filtered = []

        industries = filters.get("industries", [])
        keywords = filters.get("keywords", [])
        exclude_keywords = filters.get("exclude_keywords", [])
        min_budget = filters.get("min_budget", 0)
        regions = filters.get("regions", [])

        for bid in bids:
            # 行业过滤
            if industries:
                crm_industry = bid.get("crm_industry", "")
                if not any(ind in crm_industry for ind in industries):
                    continue

            # 关键词过滤
            title = bid.get("title", "")
            if keywords and not any(kw in title for kw in keywords):
                continue

            # 排除关键词
            if exclude_keywords and any(kw in title for kw in exclude_keywords):
                continue

            # 预算过滤
            budget = self._parse_budget(bid.get("budget", "0"))
            if min_budget > 0 and budget < min_budget:
                continue

            # 地区过滤
            if regions:
                region = bid.get("region", "")
                if not any(r in region for r in regions):
                    continue

            filtered.append(bid)

        return filtered

    def _parse_budget(self, budget_str: str) -> float:
        """解析预算字符串"""
        try:
            # 移除非数字字符
            import re
            numbers = re.findall(r'[\d.]+', str(budget_str))
            if numbers:
                return float(numbers[0])
        except:
            pass
        return 0.0

    def _llm_classify(self, bids: List[Dict], filters: Dict) -> List[Dict]:
        """使用LLM进行智能分类"""
        # 批量处理，每次最多10条
        batch_size = 10
        classified_bids = []

        for i in range(0, len(bids), batch_size):
            batch = bids[i:i + batch_size]
            # 这里可以调用LLM进行分类判断
            # 目前先返回原数据
            classified_bids.extend(batch)

        return classified_bids
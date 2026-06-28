"""
分发智能体 - 负责消息发送和路由
"""
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentResult
from dingtalk.sender import DingTalkSender
import logging

logger = logging.getLogger(__name__)


class DispatchAgent(BaseAgent):
    """分发智能体"""

    name = "dispatch_agent"
    description = "负责标讯消息发送，支持按规则路由到不同钉钉群"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.sender = DingTalkSender()

    def execute(self, task_data: Dict[str, Any]) -> AgentResult:
        """
        执行分发任务

        Args:
            task_data: {
                "bids": [...],
                "groups": [
                    {
                        "name": "金融能源群",
                        "webhook_url": "https://oapi.dingtalk.com/...",
                        "industries": ["金融", "能源"]
                    }
                ],
                "message_template": "default"  # default/simple/detailed
            }
        """
        bids = task_data.get("bids", [])
        groups = task_data.get("groups", [])
        template = task_data.get("message_template", "default")

        if not bids:
            return AgentResult(
                success=True,
                message="无数据需要发送",
                data={"sent_count": 0}
            )

        if not groups:
            return AgentResult(
                success=False,
                message="未配置钉钉群",
                error="No DingTalk groups configured"
            )

        try:
            results = []
            total_sent = 0

            for group in groups:
                # 按行业筛选标讯
                group_bids = self._filter_by_industry(bids, group.get("industries", []))

                if not group_bids:
                    logger.info(f"群 {group['name']} 无匹配标讯，跳过")
                    continue

                # 格式化消息
                message = self._format_message(group_bids, template)

                # 发送消息
                success = self.sender.send_to_group(
                    webhook_url=group["webhook_url"],
                    message=message
                )

                results.append({
                    "group": group["name"],
                    "success": success,
                    "count": len(group_bids)
                })

                if success:
                    total_sent += len(group_bids)

            return AgentResult(
                success=True,
                message=f"成功发送 {total_sent} 条标讯到钉钉群",
                data={"results": results, "total_sent": total_sent}
            )

        except Exception as e:
            logger.error(f"分发失败: {e}")
            return AgentResult(
                success=False,
                message="分发失败",
                error=str(e)
            )

    def _filter_by_industry(self, bids: List[Dict], industries: List[str]) -> List[Dict]:
        """按行业筛选标讯"""
        if not industries:
            return bids

        filtered = []
        for bid in bids:
            crm_industry = bid.get("crm_industry", "")
            # 检查是否匹配任一行业
            for industry in industries:
                if industry in crm_industry:
                    filtered.append(bid)
                    break

        return filtered

    def _format_message(self, bids: List[Dict], template: str) -> str:
        """格式化消息"""
        # 统一使用DingTalkSender的格式化方法
        return self.sender.format_bid_message(bids)
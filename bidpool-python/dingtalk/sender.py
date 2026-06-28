"""
钉钉消息发送模块
"""
import requests
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DingTalkSender:
    """钉钉消息发送器"""

    def __init__(self):
        self.timeout = 30

    def send_to_group(self, webhook_url: str, message: str, msgtype: str = "text") -> bool:
        """
        发送消息到钉钉群

        Args:
            webhook_url: 钉钉机器人Webhook URL
            message: 消息内容
            msgtype: 消息类型 (text/markdown/link)

        Returns:
            是否发送成功
        """
        try:
            if msgtype == "text":
                payload = {
                    "msgtype": "text",
                    "text": {
                        "content": message
                    }
                }
            elif msgtype == "markdown":
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": "标讯通知",
                        "text": message
                    }
                }
            else:
                payload = {
                    "msgtype": "text",
                    "text": {
                        "content": message
                    }
                }

            headers = {'Content-Type': 'application/json'}

            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            result = response.json()

            if result.get('errcode') == 0:
                logger.info("钉钉消息发送成功")
                return True
            else:
                logger.error(f"钉钉消息发送失败: {result.get('errmsg', '未知错误')}")
                return False

        except Exception as e:
            logger.error(f"发送钉钉消息异常: {e}")
            return False

    def send_text(self, webhook_url: str, content: str) -> bool:
        """发送文本消息"""
        return self.send_to_group(webhook_url, content, "text")

    def send_markdown(self, webhook_url: str, title: str, content: str) -> tuple:
        """
        发送Markdown消息

        Returns:
            (success: bool, error_message: str)
        """
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }

        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=self.timeout)
            result = response.json()

            if result.get('errcode') == 0:
                return True, ""
            else:
                errmsg = result.get('errmsg', '未知错误')
                logger.error(f"钉钉返回错误: errcode={result.get('errcode')}, errmsg={errmsg}")
                return False, f"钉钉错误: {errmsg} (错误码: {result.get('errcode')})"
        except Exception as e:
            logger.error(f"发送Markdown消息失败: {e}")
            return False, str(e)

    def send_link(self, webhook_url: str, title: str, text: str, message_url: str, pic_url: str = "") -> bool:
        """发送链接消息"""
        payload = {
            "msgtype": "link",
            "link": {
                "title": title,
                "text": text,
                "messageUrl": message_url,
                "picUrl": pic_url
            }
        }

        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=self.timeout)
            result = response.json()
            return result.get('errcode') == 0
        except Exception as e:
            logger.error(f"发送链接消息失败: {e}")
            return False

    def send_action_card(self, webhook_url: str, title: str, text: str, buttons: List[Dict]) -> bool:
        """
        发送ActionCard消息

        Args:
            webhook_url: Webhook URL
            title: 标题
            text: 内容
            buttons: 按钮列表 [{"title": "...", "actionURL": "..."}]
        """
        if len(buttons) == 1:
            payload = {
                "msgtype": "actionCard",
                "actionCard": {
                    "title": title,
                    "text": text,
                    "singleTitle": buttons[0]["title"],
                    "singleURL": buttons[0]["actionURL"]
                }
            }
        else:
            btns = [{"title": b["title"], "actionURL": b["actionURL"]} for b in buttons]
            payload = {
                "msgtype": "actionCard",
                "actionCard": {
                    "title": title,
                    "text": text,
                    "btnOrientation": "0",
                    "btns": btns
                }
            }

        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=self.timeout)
            result = response.json()
            return result.get('errcode') == 0
        except Exception as e:
            logger.error(f"发送ActionCard失败: {e}")
            return False

    def format_bid_message(self, bids: List[Dict[str, Any]]) -> str:
        """
        格式化标讯消息为Markdown格式（美观版）

        Args:
            bids: 标讯列表

        Returns:
            格式化的消息内容
        """
        if not bids:
            return "暂无招标信息"

        message = f"## 📋 招标信息推送\n\n"
        message += f"共推送 **{len(bids)}** 条招标信息\n\n"
        message += "---\n\n"

        for i, bid in enumerate(bids, 1):
            title = bid.get('title', '未知标题')

            # 标题和序号
            message += f"**{i}. {title}**\n\n"

            # 预算（必填）
            budget = bid.get('budget', '')
            if not budget or budget == '0' or budget == '0.0':
                budget = '未公开'
            message += f"💰 **预算**: {budget}\n"

            # 开标时间（必填）
            open_date = bid.get('open_date', '')
            if not open_date:
                open_date = '暂无'
            elif len(open_date) > 10:
                open_date = open_date[:10]
            message += f"⏰ **开标时间**: {open_date}\n"

            # 招标单位（可选）
            tender_unit = bid.get('tender_unit', '')
            if tender_unit:
                # 限制长度，避免太长影响阅读
                if len(tender_unit) > 40:
                    tender_unit = tender_unit[:40] + '...'
                message += f"🏢 **招标单位**: {tender_unit}\n"

            # 地区（可选）
            region = bid.get('region', '')
            if region:
                message += f"📍 **地区**: {region}\n"

            # 链接（必填）
            link = bid.get('link', '')
            if link:
                message += f"🔗 [查看详情]({link})\n\n"
            else:
                message += "\n"

        return message

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
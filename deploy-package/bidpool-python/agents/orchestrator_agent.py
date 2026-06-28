"""
编排智能体 - 负责协调其他Agent执行，支持多轮对话记忆
"""
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentResult
from agents.crawler_agent import CrawlerAgent
from agents.filter_agent import FilterAgent
from agents.dispatch_agent import DispatchAgent
from llm.claude_client import LLMClient
from llm.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from llm.conversation_memory import get_memory, ConversationMemory
import logging
import json
import requests
import os

logger = logging.getLogger(__name__)

# Go后端API地址
GO_API_URL = os.environ.get("GO_API_URL", "http://localhost:8080")


class OrchestratorAgent(BaseAgent):
    """编排智能体 - 支持多轮对话"""

    name = "orchestrator_agent"
    description = "负责协调其他Agent执行，处理用户对话指令"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.llm_client = LLMClient()
        self.memory = get_memory()

        # 初始化其他Agent
        self.crawler_agent = CrawlerAgent(config)
        self.filter_agent = FilterAgent(config)
        self.dispatch_agent = DispatchAgent(config)

    def execute(self, task_data: Dict[str, Any]) -> AgentResult:
        """执行编排任务"""
        action = task_data.get("action", "full_pipeline")
        params = task_data.get("params", {})

        if action == "full_pipeline":
            return self._run_full_pipeline(params)
        elif action == "collect":
            return self.crawler_agent.run(params)
        elif action == "filter":
            return self.filter_agent.run(params)
        elif action == "dispatch":
            return self.dispatch_agent.run(params)
        else:
            return AgentResult(
                success=False,
                message=f"未知操作: {action}",
                error="Unknown action"
            )

    def process_chat(self, message: str, session_id: str = "default", context: Optional[Dict] = None) -> str:
        """处理对话消息 - 支持多轮记忆"""
        try:
            # 记录用户消息
            self.memory.add_message(session_id, "user", message)

            # 获取当前对话状态
            stage = self.memory.get_stage(session_id)
            pending_data = self.memory.get_pending_data(session_id)

            # 根据当前阶段处理消息
            if stage == "waiting_group":
                return self._handle_group_selection(message, session_id)
            elif stage == "waiting_bids_filter":
                return self._handle_bids_filter(message, session_id)
            elif stage == "waiting_confirm":
                return self._handle_confirm(message, session_id)

            # 新请求 - 解析意图
            intent = self._parse_intent_with_context(message, session_id)

            if intent["type"] == "query_bids":
                response = self._handle_query_bids(intent["params"])
            elif intent["type"] == "collect_bids":
                response = self._handle_collect(intent["params"])
            elif intent["type"] == "send_bids":
                # 检查是否提供了完整参数（地区+群名称）
                params = intent["params"]
                if params.get("region") and params.get("group_name"):
                    # 参数完整，直接发送
                    response = self._handle_send_with_params(params, session_id)
                else:
                    # 参数不完整，启动多轮确认流程
                    response = self._start_send_flow(session_id)
            elif intent["type"] == "query_status":
                response = self._handle_status_query()
            elif intent["type"] == "query_tasks":
                response = self._handle_query_tasks()
            elif intent["type"] == "cancel":
                self.memory.clear_state(session_id)
                response = "已取消当前操作。有什么其他需要帮助的吗？"
            else:
                response = self._chat_with_llm(message, session_id)

            # 记录助手回复
            self.memory.add_message(session_id, "assistant", response)
            return response

        except Exception as e:
            logger.error(f"对话处理失败: {e}")
            import traceback
            traceback.print_exc()
            return f"处理失败: {str(e)}"

    def _parse_intent_with_context(self, message: str, session_id: str) -> Dict:
        """结合上下文解析意图"""
        history = self.memory.get_history(session_id)

        # 如果有历史对话，让 LLM 考虑上下文
        if len(history) > 0:
            context_str = "\n".join([
                f"{h['role']}: {h['content'][:100]}"
                for h in history[-4:]  # 最近4轮
            ])

            prompt = f"""结合对话历史，分析用户最新消息的意图。

对话历史:
{context_str}

用户最新消息: {message}

请返回JSON格式：
{{"type": "意图类型", "params": {{参数}}}}

意图类型：
- query_bids: 查询/查看标讯
- collect_bids: 收集/爬取标讯
- send_bids: 发送标讯到钉钉
- query_status: 查询系统状态
- query_tasks: 查询任务列表
- cancel: 取消当前操作
- chat: 普通对话

只返回JSON，不要其他内容。"""

            try:
                response = self.llm_client.chat(prompt)
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                logger.error(f"LLM解析意图失败: {e}")

        # 降级到简单解析
        return self._parse_intent_simple(message)

    def _parse_intent_simple(self, message: str) -> Dict:
        """简单意图解析"""
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["取消", "不用了", "放弃", "算了"]):
            return {"type": "cancel", "params": {}}
        elif any(kw in message_lower for kw in ["查看标讯", "有哪些标讯", "标讯列表", "查询标讯", "看一下标讯"]):
            params = {}
            for name in ["重庆", "四川", "云南", "贵州", "西藏"]:
                if name in message:
                    params["region"] = name
            return {"type": "query_bids", "params": params}
        elif any(kw in message_lower for kw in ["收集", "爬取", "抓取", "采集", "抓标讯"]):
            return {"type": "collect_bids", "params": self._extract_params(message)}
        elif any(kw in message_lower for kw in ["发送", "推送", "通知", "推送到钉钉", "分发", "发到钉钉", "钉钉"]):
            # 尝试从消息中提取地区和群名称
            params = self._extract_send_params(message)
            return {"type": "send_bids", "params": params}
        elif any(kw in message_lower for kw in ["状态", "查询状态", "系统状态"]):
            return {"type": "query_status", "params": {}}
        elif any(kw in message_lower for kw in ["任务", "任务列表", "查看任务"]):
            return {"type": "query_tasks", "params": {}}

        return {"type": "chat", "params": {}}

    def _start_send_flow(self, session_id: str) -> str:
        """启动发送流程 - 询问目标钉钉群"""
        try:
            # 获取钉钉群配置
            config_response = requests.get(f"{GO_API_URL}/api/v1/config", timeout=10)
            if config_response.status_code != 200:
                return "### ❌ 获取配置失败\n\n无法获取钉钉群配置，请稍后重试。"

            config_data = config_response.json()
            groups = config_data.get("data", {}).get("dingtalk_groups", [])

            if not groups:
                return "### ⚠️ 未配置钉钉群\n\n请先在设置页面添加钉钉群。"

            # 设置状态为等待选择群
            self.memory.set_stage(session_id, "waiting_group", {
                "groups": groups
            })

            # 构建群选择提示
            group_list = "\n".join([
                f"  {i+1}. **{g.get('name')}**（行业: {', '.join(g.get('industries', [])) or '全部'}）"
                for i, g in enumerate(groups)
            ])

            return f"""### 📤 发送标讯到钉钉

请选择要发送到哪个钉钉群：

{group_list}

> 请回复群名称或序号（如：**测试** 或 **1**）。回复「取消」可退出。"""

        except Exception as e:
            logger.error(f"启动发送流程失败: {e}")
            return f"启动发送流程失败: {str(e)}"

    def _handle_group_selection(self, message: str, session_id: str) -> str:
        """处理群选择"""
        pending_data = self.memory.get_pending_data(session_id)
        groups = pending_data.get("groups", [])

        # 尝试匹配群名称或序号
        selected_group = None
        message_lower = message.lower().strip()

        # 检查取消
        if any(kw in message_lower for kw in ["取消", "不用了", "算了"]):
            self.memory.clear_state(session_id)
            return "已取消发送操作。"

        # 尝试序号匹配
        try:
            index = int(message_lower) - 1
            if 0 <= index < len(groups):
                selected_group = groups[index]
        except:
            pass

        # 尝试名称匹配
        if not selected_group:
            for g in groups:
                if g.get("name", "").lower() in message_lower or message_lower in g.get("name", "").lower():
                    selected_group = g
                    break

        if not selected_group:
            group_names = ", ".join([g.get("name") for g in groups])
            return f"未识别到有效的群名称。请回复群名称（{group_names})或序号，或回复「取消」。"

        # 保存选择的群，询问标讯筛选条件
        self.memory.update_pending_data(session_id, {
            "selected_group": selected_group
        })
        self.memory.set_stage(session_id, "waiting_bids_filter")

        return f"""### ✅ 已选择群：{selected_group.get('name')}

请选择要发送哪些标讯：

1. **全部待发送标讯**
2. **指定地区**（如：重庆）
3. **指定行业**（如：医疗、政府）
4. **最近收集的标讯**

> 请回复选项或筛选条件。回复「取消」可退出。"""

    def _handle_bids_filter(self, message: str, session_id: str) -> str:
        """处理标讯筛选"""
        message_lower = message.lower().strip()

        # 检查取消
        if any(kw in message_lower for kw in ["取消", "不用了", "算了"]):
            self.memory.clear_state(session_id)
            return "已取消发送操作。"

        # 获取标讯
        try:
            params = {"status": "pending"}

            # 解析筛选条件
            if "全部" in message_lower or "所有" in message_lower:
                pass  # 不添加额外筛选
            elif "最近" in message_lower:
                params["limit"] = 10
            else:
                # 尝试地区或行业筛选
                regions = ["重庆", "四川", "云南", "贵州", "西藏", "西藏自治区", "那曲", "拉萨"]
                for r in regions:
                    if r in message:
                        params["region"] = r
                        break

                industries = ["医疗", "政府", "金融", "教育", "通信", "能源", "企业"]
                for ind in industries:
                    if ind in message:
                        params["crm_industry"] = ind
                        break

            response = requests.get(f"{GO_API_URL}/api/v1/bids", params=params, timeout=10)
            if response.status_code != 200:
                return "获取标讯失败，请稍后重试。"

            data = response.json()
            bids = data.get("data", [])

            if not bids:
                # 尝试获取所有标讯
                response = requests.get(f"{GO_API_URL}/api/v1/bids", timeout=10)
                data = response.json()
                bids = data.get("data", [])
                if not bids:
                    self.memory.clear_state(session_id)
                    return "没有找到标讯。请先收集标讯后再发送。"

            # 保存待发送的标讯
            pending_data = self.memory.get_pending_data(session_id)
            selected_group = pending_data.get("selected_group")

            self.memory.update_pending_data(session_id, {
                "bids_to_send": bids[:10]  # 最多10条
            })
            self.memory.set_stage(session_id, "waiting_confirm")

            # 构建确认信息
            bid_preview = "\n".join([
                f"  {i+1}. {b.get('title', '未知')[:30]}..."
                for i, b in enumerate(bids[:10])
            ])

            return f"""### 📋 确认发送

**目标群**: {selected_group.get('name')}
**标讯数量**: {len(bids[:10])} 条

待发送标讯：
{bid_preview}

> 请回复「确认」发送，或回复「取消」退出。"""

        except Exception as e:
            logger.error(f"获取标讯失败: {e}")
            return f"获取标讯失败: {str(e)}"

    def _handle_confirm(self, message: str, session_id: str) -> str:
        """处理确认发送"""
        message_lower = message.lower().strip()

        # 检查取消
        if any(kw in message_lower for kw in ["取消", "不用了", "算了", "不发送", "不确认"]):
            self.memory.clear_state(session_id)
            return "已取消发送操作。"

        # 检查确认
        if any(kw in message_lower for kw in ["确认", "发送", "是的", "对", "好的", "ok", "yes"]):
            pending_data = self.memory.get_pending_data(session_id)
            selected_group = pending_data.get("selected_group")
            bids_to_send = pending_data.get("bids_to_send", [])

            if not selected_group or not bids_to_send:
                self.memory.clear_state(session_id)
                return "数据丢失，请重新开始发送流程。"

            try:
                # 调用发送API
                send_data = {
                    "bids": bids_to_send,
                    "webhook_url": selected_group.get("webhook_url"),
                    "format": "simple"
                }

                send_response = requests.post(
                    f"{GO_API_URL}/api/v1/bids/dispatch",
                    json=send_data,
                    timeout=30
                )

                self.memory.clear_state(session_id)

                if send_response.status_code == 200:
                    result = send_response.json()
                    if result.get("code") == 0:
                        return f"""### ✅ 发送成功

成功发送 **{len(bids_to_send)}** 条标讯到钉钉群「{selected_group.get('name')}」。

> 如需继续操作，请输入新的指令。"""
                    else:
                        return f"发送失败: {result.get('message', '未知错误')}"
                else:
                    return f"发送请求失败: HTTP {send_response.status_code}"

            except Exception as e:
                self.memory.clear_state(session_id)
                return f"发送失败: {str(e)}"

        # 未识别的回复
        return "请回复「确认」发送，或「取消」退出。"

    def _handle_query_bids(self, params: Dict) -> str:
        """查询标讯"""
        try:
            query_params = {}
            if params.get("region"):
                query_params["region"] = params["region"]
            if params.get("industry"):
                query_params["crm_industry"] = params["industry"]

            response = requests.get(f"{GO_API_URL}/api/v1/bids", params=query_params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    bids = data.get("data", [])
                    total = data.get("total", 0)

                    if not bids:
                        return "当前没有找到符合条件的标讯。"

                    result = f"### 📋 标讯列表\n\n找到 **{total}** 条标讯：\n\n---\n\n"
                    for i, bid in enumerate(bids[:10], 1):
                        title = bid.get('title', '未知标题')
                        tender = bid.get('tender_unit', '未知')
                        industry = bid.get('crm_industry', '未知')
                        budget = bid.get('budget', '未公布')
                        region = bid.get('region', '未知')
                        publish_date = bid.get('publish_date', '未知')

                        if budget and budget != '未公布':
                            try:
                                budget_str = f"{float(budget):,.0f} 元"
                            except:
                                budget_str = budget
                        else:
                            budget_str = "未公布"

                        result += f"**{i}. {title}**\n\n"
                        result += f"| 属性 | 内容 |\n"
                        result += f"| --- | --- |\n"
                        result += f"| 🏢 招标单位 | {tender} |\n"
                        result += f"| 🏷️ 行业 | {industry} |\n"
                        result += f"| 💰 预算 | {budget_str} |\n"
                        result += f"| 📍 地区 | {region} |\n"
                        result += f"| 📅 发布时间 | {publish_date} |\n\n"

                    if total > 10:
                        result += f"---\n\n> 还有 **{total - 10}** 条标讯未显示。"

                    return result
                else:
                    return f"查询失败: {data.get('message', '未知错误')}"
            else:
                return f"API请求失败: HTTP {response.status_code}"

        except Exception as e:
            logger.error(f"查询标讯失败: {e}")
            return f"查询标讯失败: {str(e)}"

    def _handle_query_tasks(self) -> str:
        """查询任务列表"""
        try:
            response = requests.get(f"{GO_API_URL}/api/v1/tasks", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    tasks = data.get("data", [])

                    if not tasks:
                        return "当前没有任务。"

                    result = f"### 📝 任务列表\n\n共有 **{len(tasks)}** 个任务：\n\n---\n\n"
                    for i, task in enumerate(tasks, 1):
                        status = "✅ 启用" if task.get("enabled") else "⏸️ 禁用"
                        exec_status = task.get("execution_status", "未执行")
                        cron_expr = task.get('cron_expr', '')
                        cron_display = f"`{cron_expr}`" if cron_expr else "未设置"

                        result += f"**{i}. {task.get('name', '未知')}**\n\n"
                        result += f"| 属性 | 内容 |\n"
                        result += f"| --- | --- |\n"
                        result += f"| 🌐 平台 | {task.get('platform', '未知')} |\n"
                        result += f"| 📊 状态 | {status} |\n"
                        result += f"| ⚡ 执行状态 | {exec_status} |\n"
                        result += f"| ⏰ 定时 | {cron_display} |\n\n"

                    return result
                else:
                    return f"查询失败: {data.get('message', '未知错误')}"
            else:
                return f"API请求失败: HTTP {response.status_code}"

        except Exception as e:
            logger.error(f"查询任务失败: {e}")
            return f"查询任务失败: {str(e)}"

    def _chat_with_llm(self, message: str, session_id: str) -> str:
        """使用LLM进行对话 - 带历史上下文"""
        history = self.memory.get_history(session_id)

        # 构建带历史的对话
        history_context = "\n".join([
            f"{h['role']}: {h['content']}"
            for h in history[-6:]  # 最近6轮
        ])

        system_prompt = """你是标讯平台的智能助手。你可以帮助用户：
1. 查看标讯 - 查询数据库中的标讯信息
2. 收集标讯 - 从千里马等平台爬取招标信息
3. 发送通知 - 将标讯推送到钉钉群（需要多步确认）
4. 任务管理 - 查看定时任务列表

请使用 Markdown 格式回复，保持简洁友好。

发送标讯到钉钉是一个多步骤操作：
1. 先询问目标群
2. 再确认发送内容
3. 最后确认发送

回复时使用 Markdown 格式，如标题(###)、粗体(**)、列表、引用块(>)等。"""

        try:
            # 使用带历史的对话
            full_messages = []
            if history_context:
                full_messages.append({"role": "system", "content": f"对话历史:\n{history_context}"})
            full_messages.append({"role": "user", "content": message})

            response = self.llm_client.chat_with_history(full_messages, system_prompt)
            return response
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return f"我是标讯平台智能助手。你可以让我查看标讯、收集标讯、发送到钉钉或查看任务列表。"

    def _extract_params(self, message: str) -> Dict:
        """从消息中提取参数"""
        params = {}
        from datetime import datetime, timedelta
        today = datetime.now()

        if "本周" in message:
            week_start = today - timedelta(days=today.weekday())
            params["start_date"] = week_start.strftime("%Y-%m-%d")
            params["end_date"] = today.strftime("%Y-%m-%d")
        elif "本月" in message:
            params["start_date"] = today.replace(day=1).strftime("%Y-%m-%d")
            params["end_date"] = today.strftime("%Y-%m-%d")

        regions = []
        region_map = {"重庆": "500000", "四川": "510000", "云南": "530000", "贵州": "520000", "西藏": "540000"}
        for name, code in region_map.items():
            if name in message:
                regions.append(code)
        if regions:
            params["region_codes"] = regions

        return params

    def _extract_send_params(self, message: str) -> Dict:
        """从消息中提取发送参数（地区、群名称）"""
        params = {}

        # 提取地区
        regions = ["重庆", "四川", "云南", "贵州", "西藏", "西藏自治区"]
        for r in regions:
            if r in message:
                params["region"] = r
                break

        # 提取群名称 - 支持多种表达方式
        # 匹配模式: "发送到XXX群" 或 "发送到XXX钉钉群" 或 "推送到XXX"
        import re

        # 模式1: 发送到/推送到 + 群名 + 群/钉钉群
        patterns = [
            r"发送到\s*(.+?)群",
            r"推送到\s*(.+?)群",
            r"发到\s*(.+?)群",
            r"发送到\s*(.+?)钉钉",
            r"推送到\s*(.+?)钉钉",
            r"发到\s*(.+?)钉钉",
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                group_name = match.group(1).strip()
                # 移除常见的后缀词
                group_name = re.sub(r"(钉钉|测试|通知)$", "", group_name).strip()
                if group_name:
                    params["group_name"] = group_name
                    break

        return params

    def _handle_send_with_params(self, params: Dict, session_id: str) -> str:
        """直接发送（参数已完整）"""
        try:
            region = params.get("region")
            group_name = params.get("group_name")

            # 获取钉钉群配置
            config_response = requests.get(f"{GO_API_URL}/api/v1/config", timeout=10)
            if config_response.status_code != 200:
                return "### ❌ 获取配置失败\n\n无法获取钉钉群配置，请稍后重试。"

            config_data = config_response.json()
            groups = config_data.get("data", {}).get("dingtalk_groups", [])

            if not groups:
                return "### ⚠️ 未配置钉钉群\n\n请先在设置页面添加钉钉群。"

            # 匹配群名称
            selected_group = None
            for g in groups:
                if group_name in g.get("name", "") or g.get("name", "") in group_name:
                    selected_group = g
                    break

            if not selected_group:
                group_names = ", ".join([g.get("name") for g in groups])
                return f"### ⚠️ 未找到群\n\n未找到名称包含「{group_name}」的钉钉群。\n\n可用的群：{group_names}"

            # 获取标讯
            query_params = {"status": "pending"}
            if region:
                query_params["region"] = region

            response = requests.get(f"{GO_API_URL}/api/v1/bids", params=query_params, timeout=10)
            if response.status_code != 200:
                return "获取标讯失败，请稍后重试。"

            data = response.json()
            bids = data.get("data", [])

            if not bids:
                region_text = f"{region}地区" if region else ""
                return f"### ⚠️ 无标讯可发送\n\n当前没有{region_text}待发送的标讯。"

            # 限制发送数量
            bids_to_send = bids[:10]

            # 构建预览
            bid_preview = "\n".join([
                f"  {i+1}. {b.get('title', '未知')[:30]}..."
                for i, b in enumerate(bids_to_send)
            ])

            region_text = f"**{region}**地区" if region else "全部"

            # 直接发送
            send_data = {
                "bids": bids_to_send,
                "webhook_url": selected_group.get("webhook_url"),
                "format": "simple"
            }

            send_response = requests.post(
                f"{GO_API_URL}/api/v1/bids/dispatch",
                json=send_data,
                timeout=30
            )

            if send_response.status_code == 200:
                result = send_response.json()
                if result.get("code") == 0:
                    return f"""### ✅ 发送成功

**目标群**: {selected_group.get('name')}
**筛选条件**: {region_text}
**发送数量**: {len(bids_to_send)} 条

已发送的标讯：
{bid_preview}

> 如需继续操作，请输入新的指令。"""
                else:
                    return f"发送失败: {result.get('message', '未知错误')}"
            else:
                return f"发送请求失败: HTTP {send_response.status_code}"

        except Exception as e:
            logger.error(f"直接发送失败: {e}")
            return f"发送失败: {str(e)}"

    def _run_full_pipeline(self, params: Dict) -> AgentResult:
        """运行完整流程"""
        results = []
        logger.info("开始爬取...")
        crawl_result = self.crawler_agent.run(params)
        if not crawl_result.success:
            return crawl_result
        results.append(("crawl", crawl_result))

        logger.info("开始过滤...")
        filter_result = self.filter_agent.run({"bids": crawl_result.data.get("bids", []), "filters": params.get("filters", {})})
        if not filter_result.success:
            return filter_result
        results.append(("filter", filter_result))

        logger.info("开始分发...")
        dispatch_result = self.dispatch_agent.run({"bids": filter_result.data.get("bids", []), "groups": params.get("dingtalk_groups", [])})
        results.append(("dispatch", dispatch_result))

        return AgentResult(success=True, message="完整流程执行完成", data={"results": results})

    def _handle_collect(self, params: Dict) -> str:
        """处理收集请求"""
        result = self.crawler_agent.run(params)
        if result.success:
            return f"收集完成: {result.message}"
        return f"收集失败: {result.error or result.message}"

    def _handle_send(self, params: Dict) -> str:
        """处理发送请求"""
        result = self.dispatch_agent.run(params)
        if result.success:
            return f"发送完成: {result.message}"
        return f"发送失败: {result.error or result.message}"

    def _handle_status_query(self) -> str:
        """处理状态查询"""
        try:
            response = requests.get(f"{GO_API_URL}/api/v1/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    status_data = data.get("data", {})
                    return f"""### 📊 系统状态

| 指标 | 数值 |
| --- | --- |
| 📋 标讯总数 | {status_data.get('bid_count', 0)} |
| 📝 任务数量 | {status_data.get('task_count', 0)} |
| ⚡ 活跃任务 | {len(status_data.get('active_jobs', []))} |
| 🕐 服务器时间 | {status_data.get('server_time', '未知')} |

> 系统运行正常 ✅"""
        except Exception as e:
            pass
        return "系统运行正常。你可以让我查看标讯、收集标讯或发送通知。"
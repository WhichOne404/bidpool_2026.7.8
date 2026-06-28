"""
Agent API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from agents.filter_agent import FilterAgent
from agents.dispatch_agent import DispatchAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.monitor_agent import MonitorAgent
import logging
import asyncio
import json
import sys
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

router = APIRouter()

# 线程池执行器，用于运行同步代码（非Playwright任务）
executor = ThreadPoolExecutor(max_workers=4)

# 初始化Agents（filter/dispatch/monitor无需浏览器，可在主进程初始化）
filter_agent = FilterAgent()
dispatch_agent = DispatchAgent()
orchestrator_agent = OrchestratorAgent()
monitor_agent = MonitorAgent()


class CrawlerRequest(BaseModel):
    """爬虫请求"""
    platform: str = "qianlima"
    region_codes: List[str] = ["500000"]
    start_date: str = ""
    end_date: str = ""
    credentials: Optional[Dict[str, str]] = None


class FilterRequest(BaseModel):
    """过滤请求"""
    bids: List[Dict[str, Any]]
    filters: Optional[Dict[str, Any]] = None


class DispatchRequest(BaseModel):
    """分发请求"""
    bids: List[Dict[str, Any]]
    groups: List[Dict[str, Any]]
    message_template: str = "default"


class DispatchSendRequest(BaseModel):
    """直接发送请求"""
    webhook_url: str
    bids: List[Dict[str, Any]]


class PipelineRequest(BaseModel):
    """完整流程请求"""
    platform: str = "qianlima"
    region_codes: List[str] = ["500000"]
    start_date: str = ""
    end_date: str = ""
    credentials: Optional[Dict[str, str]] = None
    filters: Optional[Dict[str, Any]] = None
    dingtalk_groups: Optional[List[Dict[str, Any]]] = None


@router.post("/crawler/execute")
async def execute_crawler(request: CrawlerRequest):
    """执行爬虫任务"""
    task_data = {
        "platform": request.platform,
        "region_codes": request.region_codes,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "credentials": request.credentials or {}
    }

    logger.info(f"收到爬虫请求: platform={request.platform}, region_codes={request.region_codes}, start_date={request.start_date}, end_date={request.end_date}")

    # 使用 subprocess 在完全隔离的子进程中运行 Playwright 爬虫
    # ProcessPoolExecutor 的 spawn 模式在 uvicorn 环境中也会继承 asyncio 事件循环
    result = await _run_crawler_subprocess(task_data)

    return {
        "code": 0 if result.success else -1,
        "message": result.message,
        "data": result.data,
        "bids_count": result.data.get("count", 0) if result.data else 0
    }


async def _run_crawler_subprocess(task_data):
    """通过 subprocess 在完全隔离的进程中运行爬虫"""
    from agents.base import AgentResult

    runner_path = "/app/crawlers/runner.py"
    # 为结果文件生成唯一路径
    result_file = os.path.join(tempfile.gettempdir(), f"crawl_result_{os.getpid()}_{id({})}.json")
    task_data["_result_file"] = result_file
    task_json = json.dumps(task_data, ensure_ascii=False)

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, runner_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=task_json.encode("utf-8")),
            timeout=180
        )

        if proc.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="replace")[:2000]
            logger.error(f"爬虫子进程异常退出(code={proc.returncode}): {stderr_text}")
            _safe_remove(result_file)
            return AgentResult(
                success=False,
                message=f"爬虫子进程异常退出",
                error=stderr_text
            )

        if stderr:
            stderr_text = stderr.decode("utf-8", errors="replace")
            for line in stderr_text.split("\n"):
                if line.strip():
                    logger.info(f"[crawler] {line.strip()}")

        # 从临时文件中读取结果（避免库的 print() 与 JSON 在 stdout 中混合）
        if os.path.exists(result_file):
            with open(result_file, "r", encoding="utf-8") as f:
                output = f.read()
            _safe_remove(result_file)
        else:
            output = stdout.decode("utf-8", errors="replace").strip()

        if not output:
            return AgentResult(
                success=False,
                message="爬虫子进程无输出",
                error="Empty output"
            )

        result_data = json.loads(output)
        return AgentResult(
            success=result_data.get("success", False),
            message=result_data.get("message", ""),
            data=result_data.get("data"),
            error=result_data.get("error")
        )

    except asyncio.TimeoutError:
        logger.error("爬虫子进程超时(180s)")
        proc.kill()
        _safe_remove(result_file)
        return AgentResult(
            success=False,
            message="爬虫超时",
            error="Timeout"
        )
    except Exception as e:
        logger.error(f"爬虫子进程异常: {e}")
        _safe_remove(result_file)
        return AgentResult(
            success=False,
            message="爬虫执行异常",
            error=str(e)
        )


def _safe_remove(path):
    """安全删除临时文件"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@router.post("/filter/execute")
async def execute_filter(request: FilterRequest):
    """执行过滤任务"""
    task_data = {
        "bids": request.bids,
        "filters": request.filters or {}
    }

    result = filter_agent.run(task_data)

    return {
        "code": 0 if result.success else -1,
        "message": result.message,
        "data": result.data
    }


@router.post("/dispatch/execute")
async def execute_dispatch(request: DispatchRequest):
    """执行分发任务"""
    task_data = {
        "bids": request.bids,
        "groups": request.groups,
        "message_template": request.message_template
    }

    result = dispatch_agent.run(task_data)

    return {
        "code": 0 if result.success else -1,
        "message": result.message,
        "data": result.data
    }


@router.post("/dispatch/send")
async def send_to_dingtalk(request: DispatchSendRequest):
    """直接发送标讯到钉钉"""
    from dingtalk.sender import DingTalkSender

    sender = DingTalkSender()

    # 格式化消息为Markdown
    message = sender.format_bid_message(request.bids)

    # 检查消息字节大小，钉钉限制20000bytes
    message_bytes = len(message.encode('utf-8'))
    logger.info(f"消息字节大小: {message_bytes}, 标讯数量: {len(request.bids)}")

    if message_bytes > 19000:
        # 分批发送 - 每批10条标讯，确保不超限
        logger.info(f"消息字节大小 {message_bytes} 超过限制，将分批发送")

        batch_size = 10  # 每批最多10条，确保美观格式的安全性
        chunks = []

        for i in range(0, len(request.bids), batch_size):
            batch_bids = request.bids[i:i+batch_size]
            batch_message = sender.format_bid_message(batch_bids)
            batch_num = i // batch_size + 1
            total_batches = (len(request.bids) - 1) // batch_size + 1

            # 更新标题，添加批次信息
            batch_message = batch_message.replace(
                "## 📋 标讯推送\n\n",
                f"## 📋 标讯推送（第 {batch_num}/{total_batches} 批）\n\n"
            )

            chunks.append({
                'message': batch_message,
                'title': f"标讯推送 ({batch_num}/{total_batches})",
                'count': len(batch_bids),
                'bytes': len(batch_message.encode('utf-8'))
            })

        # 发送分块消息
        success_count = 0
        total_sent = 0
        for idx, chunk in enumerate(chunks, 1):
            logger.info(f"发送第 {idx} 批，字节数: {chunk['bytes']}")
            success, error_msg = sender.send_markdown(request.webhook_url, chunk['title'], chunk['message'])
            if success:
                success_count += 1
                total_sent += chunk['count']
                logger.info(f"第 {idx} 批消息发送成功，包含 {chunk['count']} 条标讯")
            else:
                logger.error(f"发送第 {idx} 批消息失败: {error_msg}")
                return {
                    "code": -1,
                    "message": f"第 {idx}/{len(chunks)} 批消息发送失败: {error_msg}"
                }

        return {
            "code": 0,
            "message": f"成功发送 {total_sent} 条标讯（分 {len(chunks)} 批发送）",
            "data": {"sent_count": total_sent, "chunks": len(chunks)}
        }
    else:
        # 单次发送
        logger.info(f"单次发送，字节数: {message_bytes}")
        success, error_msg = sender.send_markdown(request.webhook_url, "标讯推送", message)

        if success:
            return {
                "code": 0,
                "message": f"成功发送 {len(request.bids)} 条标讯",
                "data": {"sent_count": len(request.bids)}
            }
        else:
            return {
                "code": -1,
                "message": f"发送失败: {error_msg}"
            }


@router.post("/pipeline/execute")
async def execute_pipeline(request: PipelineRequest):
    """执行完整流程"""
    task_data = {
        "action": "full_pipeline",
        "params": {
            "platform": request.platform,
            "region_codes": request.region_codes,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "credentials": request.credentials or {},
            "filters": request.filters or {},
            "dingtalk_groups": request.dingtalk_groups or []
        }
    }

    result = orchestrator_agent.run(task_data)

    return {
        "code": 0 if result.success else -1,
        "message": result.message,
        "data": result.data
    }


@router.get("/platforms")
async def list_platforms():
    """获取可用平台列表"""
    platforms = crawler_agent.get_available_platforms()
    return {
        "code": 0,
        "data": {"platforms": platforms}
    }


@router.get("/status")
async def get_status():
    """获取Agent状态"""
    result = monitor_agent.run({"action": "health_check"})
    return {
        "code": 0,
        "data": result.data
    }
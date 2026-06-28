"""
爬虫子进程入口 - 在完全隔离的环境中运行 Playwright 爬虫
通过 stdin 接收任务数据，通过临时文件返回 JSON 结果
（避免库的 print() 输出与 JSON 结果在 stdout 中混合）
"""
import sys, json, logging, os, tempfile

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def run():
    # 通过 stdin 读取任务数据
    task_json = sys.stdin.read()
    task_data = json.loads(task_json)

    # 将结果写入临时文件，避免与库的 print() 输出在 stdout 中混合
    result_file = task_data.pop("_result_file", None)
    if not result_file:
        result_file = os.path.join(tempfile.gettempdir(), f"crawl_result_{os.getpid()}.json")

    from agents.crawler_agent import CrawlerAgent
    from dataclasses import asdict

    agent = CrawlerAgent()
    result = agent.run(task_data)

    # 将结果转换为 JSON 可序列化格式（BidInfo 是 dataclass，需转为 dict）
    data = result.data
    if data and "bids" in data:
        data["bids"] = [asdict(b) for b in data["bids"]]

    output = json.dumps({
        "success": result.success,
        "message": result.message,
        "data": data,
        "error": result.error
    }, ensure_ascii=False, default=str)

    with open(result_file, "w", encoding="utf-8") as f:
        f.write(output)

    # 输出结果文件路径到 stdout（仅一行）
    print(result_file, flush=True)


if __name__ == "__main__":
    run()

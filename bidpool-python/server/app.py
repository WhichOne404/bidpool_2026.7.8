"""
FastAPI 服务入口
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routes import agent, chat
from config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title="BidPool Agent Service",
    description="标讯平台智能体服务",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "BidPool Agent Service",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=settings.python_service_port,
        reload=True
    )
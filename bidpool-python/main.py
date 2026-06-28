"""
主入口 - 用于直接运行服务
"""
import uvicorn
from config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=settings.python_service_port,
        reload=True,
        log_level="info"
    )
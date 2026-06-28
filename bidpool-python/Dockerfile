# 使用 Playwright 官方镜像（已包含浏览器）
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

WORKDIR /app

# 使用国内镜像源
RUN sed -i 's/ports.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 创建下载目录和运行时配置目录
RUN mkdir -p /app/downloads /app/runtime

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 创建非 root 用户 (UID 10001 避免与镜像现有用户冲突)
RUN useradd -m -u 10001 bidpool && chown -R bidpool:bidpool /app

USER bidpool

EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8001"]
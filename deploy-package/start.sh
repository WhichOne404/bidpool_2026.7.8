#!/bin/bash
cd /opt/bidpool

# 创建数据目录
mkdir -p data

# 启动Python服务
echo "Starting Python service..."
cd bidpool-python
pip3 install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt -q 2>/dev/null
nohup python3 main.py > /opt/bidpool/logs/python.log 2>&1 &
PYTHON_PID=$!
echo "Python service started (PID: $PYTHON_PID)"

# 启动Go服务
echo "Starting Go service..."
cd /opt/bidpool
nohup ./bidpool-go > /opt/bidpool/logs/go.log 2>&1 &
GO_PID=$!
echo "Go service started (PID: $GO_PID)"

echo "All services started successfully!"
echo "Access: http://your-server-ip"
echo "Login: admin / bidpool@2026"

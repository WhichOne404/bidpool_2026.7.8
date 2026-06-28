#!/bin/bash

# BidPool 启动脚本

echo "========================================="
echo "  BidPool 标讯智能平台 启动脚本"
echo "========================================="

# 检查目录
cd "$(dirname "$0")"

# 创建数据目录
mkdir -p bidpool-go/data

# 启动 Go Backend
echo "[1/3] 启动 Go Backend..."
cd bidpool-go
go run cmd/server/main.go &
GO_PID=$!
cd ..

# 等待 Go 启动
sleep 3

# 启动 Python Agents
echo "[2/3] 启动 Python Agents..."
cd bidpool-python
python3 main.py &
PYTHON_PID=$!
cd ..

# 等待 Python 启动
sleep 3

# 启动 Web Frontend
echo "[3/3] 启动 Web Frontend..."
cd bidpool-web
npm run dev &
WEB_PID=$!
cd ..

echo ""
echo "========================================="
echo "  所有服务已启动!"
echo "========================================="
echo ""
echo "  Web界面:  http://localhost:3000"
echo "  Go API:   http://localhost:8080"
echo "  Python:   http://localhost:8000"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "========================================="

# 等待子进程
trap "kill $GO_PID $PYTHON_PID $WEB_PID 2>/dev/null; exit" INT TERM
wait
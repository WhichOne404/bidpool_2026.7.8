#!/bin/bash

# BidPool 停止脚本

echo "停止 BidPool 服务..."

# 停止 Go Backend
pkill -f "go run cmd/server/main.go" 2>/dev/null
pkill -f "bidpool-go" 2>/dev/null

# 停止 Python Agents
pkill -f "python main.py" 2>/dev/null
pkill -f "bidpool-python" 2>/dev/null

# 停止 Web Frontend
pkill -f "npm run dev" 2>/dev/null
pkill -f "vite" 2>/dev/null

echo "所有服务已停止"
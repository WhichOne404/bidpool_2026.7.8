#!/bin/bash

# BidPool Docker 停止脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "停止 BidPool Docker 服务..."

docker-compose down

echo "服务已停止"
echo ""
echo "如需删除数据卷，运行:"
echo "  docker-compose down -v"
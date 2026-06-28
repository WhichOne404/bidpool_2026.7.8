#!/bin/bash

# BidPool Docker 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "========================================="
echo "  BidPool 标讯智能平台 - Docker 版"
echo "========================================="

# 创建必要的目录
mkdir -p configs/python logs

# 检查配置文件
if [ ! -f "configs/config.docker.yaml" ]; then
    echo "[!] 错误: configs/config.docker.yaml 配置文件不存在"
    echo "    请先运行 docker/build.sh 创建配置"
    exit 1
fi

# 启动服务
echo "[1/2] 启动 Docker 服务..."
docker-compose up -d

# 等待服务就绪
echo "[2/2] 等待服务启动..."
sleep 5

# 检查服务状态
docker-compose ps

echo ""
echo "========================================="
echo "  服务已启动!"
echo "========================================="
echo ""
echo "  Web界面:  http://localhost"
echo "  Go API:   http://localhost/api/v1"
echo "  Chat API: http://localhost/chat"
echo ""
echo "  登录账号: admin"
echo "  登录密码: bidpool@2026"
echo ""
echo "  查看日志: docker-compose logs -f"
echo "  停止服务: docker-compose down"
echo "========================================="
#!/bin/bash

# BidPool Docker 构建脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "========================================="
echo "  BidPool Docker 构建脚本"
echo "========================================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose 未安装"
    exit 1
fi

# 创建配置目录
echo "[1/3] 创建配置目录..."
mkdir -p configs/python
mkdir -p logs

# 检查配置文件
if [ ! -f "configs/config.docker.yaml" ]; then
    echo "[!] 警告: configs/config.docker.yaml 不存在"
    exit 1
fi

if [ ! -f "configs/python/llm_config.json" ]; then
    echo "[!] 警告: configs/python/llm_config.json 不存在"
    exit 1
fi

# 构建镜像
echo "[2/3] 构建 Docker 镜像..."
docker-compose build

echo "[3/3] 镜像构建完成"
docker images | grep bidpool || true

echo ""
echo "========================================="
echo "  构建完成!"
echo "========================================="
echo ""
echo "运行以下命令启动服务:"
echo "  ./docker/start.sh"
echo ""
echo "或使用 docker-compose:"
echo "  docker-compose up -d"
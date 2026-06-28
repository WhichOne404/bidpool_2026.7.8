# Build stage - 使用 Alpine，纯 Go 编译无需 CGO
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 使用阿里云镜像
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# 安装 git（用于下载依赖）
RUN apk add --no-cache git

# 复制依赖文件
COPY go.mod go.sum ./
RUN GOPROXY=https://goproxy.cn,direct go mod download

# 复制源代码
COPY . .

# 编译（纯 Go，无 CGO）
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o bidpool-server ./cmd/server

# Runtime stage
FROM alpine:3.19

WORKDIR /app

# 使用阿里云镜像并安装运行时依赖
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && \
    apk add --no-cache ca-certificates tzdata wget

# 创建非 root 用户
RUN addgroup -g 1000 bidpool && \
    adduser -u 1000 -G bidpool -s /bin/sh -D bidpool

# 复制编译产物
COPY --from=builder /app/bidpool-server .

# 创建数据目录
RUN mkdir -p /app/data /app/configs && chown -R bidpool:bidpool /app

USER bidpool

EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["./bidpool-server"]